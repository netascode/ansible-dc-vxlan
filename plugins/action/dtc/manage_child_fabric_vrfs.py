# Copyright (c) 2024 Cisco Systems, Inc. and its affiliates
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function


__metaclass__ = type

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase
from ansible.template import Templar
from ansible.errors import AnsibleFileNotFound
from ansible_collections.cisco.nac_dc_vxlan.plugins.filter.version_compare import version_compare
from ...plugin_utils.helper_functions import get_rest_module


import re
import json

display = Display()

# Path to Jinja template files relative to create role
MSD_CHILD_FABRIC_VRF_TEMPLATE_PATH = "/../common/templates/ndfc_vrfs/msd_fabric/child_fabric/"
MSD_CHILD_FABRIC_VRF_TEMPLATE = "/msd_child_fabric_vrf.j2"

# Currently supported VRF template config keys and their mapping to data model keys
VRF_TEMPLATE_CONFIG_MAP = {
    'advertiseHostRouteFlag': {'dm_key': 'adv_host_routes', 'default': ''},
    'advertiseDefaultRouteFlag': {'dm_key': 'adv_default_routes', 'default': ''},
    'configureStaticDefaultRouteFlag': {'dm_key': 'config_static_default_route', 'default': ''},
    'bgpPassword': {'dm_key': 'bgp_password', 'default': ''},
    'bgpPasswordKeyType': {'dm_key': 'bgp_password_key_type', 'default': ''},
    'ENABLE_NETFLOW': {'dm_key': 'netflow_enable', 'default': False},
    'NETFLOW_MONITOR': {'dm_key': 'netflow_monitor', 'default': ''},
    'trmEnabled': {'dm_key': 'trm_enable', 'default': False},
    'loopbackNumber': {'dm_key': 'rp_loopback_id', 'default': ''},
    'rpAddress': {'dm_key': 'rp_address', 'default': ''},
    'isRPAbsent': {'dm_key': 'no_rp', 'default': False},
    'isRPExternal': {'dm_key': 'rp_external', 'default': False},
    'L3VniMcastGroup': {'dm_key': 'underlay_mcast_ip', 'default': ''},
    'multicastGroup': {'dm_key': 'overlay_multicast_group', 'default': ''},
    'routeTargetImportMvpn': {'dm_key': 'import_mvpn_rt', 'default': ''},
    'routeTargetExportMvpn': {'dm_key': 'export_mvpn_rt', 'default': ''}
}


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['changed'] = False
        results['failed'] = False
        results['child_fabrics_changed'] = []

        nd_version = self._task.args["nd_version"]
        msite_data = self._task.args["msite_data"]

        # Extract major, minor, patch and patch letter from nd_version
        # that is set in nac_dc_vxlan.dtc.connectivity_check role
        # Example nd_version: "3.1.1l" or "3.2.2m"
        # where 3.1.1/3.2.2 are major.minor.patch respectively
        # and l/m are the patch letter respectively
        nd_major_minor_patch = None
        nd_patch_letter = None
        match = re.match(r'^(\d+\.\d+\.\d+)([a-z])?$', nd_version)
        if match:
            nd_major_minor_patch = match.group(1)
            nd_patch_letter = match.group(2)

        vrfs = msite_data['overlay_attach_groups']['vrfs']
        vrf_attach_groups_dict = msite_data['overlay_attach_groups']['vrf_attach_groups']

        child_fabrics = msite_data['child_fabrics_data']

        network_os = task_vars['ansible_network_os']
        rest_module = get_rest_module(network_os)
        if not rest_module:
            results['failed'] = True
            results['msg'] = f"Unsupported network_os: {network_os}"
            return results

        for vrf in vrfs:
            vrf_attach_group_switches = [
                vrf_attach_group_dict['switches']
                for vrf_attach_group_dict in vrf_attach_groups_dict
                if vrf_attach_group_dict['name'] == vrf['vrf_attach_group']
            ][0]
            vrf_attach_group_switches_mgmt_ip_addresses = [
                vrf_attach_group_switch['mgmt_ip_address']
                for vrf_attach_group_switch in vrf_attach_group_switches
            ]

            vrf_child_fabrics = vrf.get('child_fabrics', [])

            for child_fabric in child_fabrics.keys():
                # Need to get the child fabric type and ensure it is a VXLAN fabric type
                # Checking for VXLAN fabric type rules out the possibility of a child fabric being an External or other type of fabric type
                child_fabric_type = child_fabrics[child_fabric]['type']
                if child_fabric_type in ['Switch_Fabric']:
                    child_fabric_attributes = child_fabrics[child_fabric]['attributes']
                    child_fabric_switches = child_fabrics[child_fabric]['switches']
                    child_fabric_switches_mgmt_ip_addresses = [child_fabric_switch['mgmt_ip_address'] for child_fabric_switch in child_fabric_switches]

                    is_intersection = set(vrf_attach_group_switches_mgmt_ip_addresses).intersection(set(child_fabric_switches_mgmt_ip_addresses))

                    if is_intersection:
                        # If switch intersection is found, then process the VRF configuration for the child fabric
                        vrf_child_fabric = []
                        if vrf_child_fabrics:
                            vrf_child_fabric = [
                                vrf_child_fabric_dict
                                for vrf_child_fabric_dict in vrf_child_fabrics
                                if (vrf_child_fabric_dict['name'] == child_fabric)
                            ]

                        if len(vrf_child_fabric) == 0:
                            # There are no matching child fabrics for this VRF.
                            # Set vrf_child_fabric to empty dict for further processing.
                            vrf_child_fabric = {}
                        elif len(vrf_child_fabric) == 1:
                            vrf_child_fabric = vrf_child_fabric[0]

                        # Need to clean these up and make them more dynamic
                        # Check if fabric settings are properly enabled
                        if vrf_child_fabric.get('netflow_enable'):
                            if child_fabric_attributes['ENABLE_NETFLOW'] == 'false':
                                error_msg = (
                                    f"For fabric {child_fabric}; NetFlow is not enabled in the fabric settings. "
                                    "To enable NetFlow in VRF, you need to first enable it in the fabric settings."
                                )
                                display.error(error_msg)
                                results['failed'] = True
                                results['msg'] = error_msg
                                return results

                        if vrf_child_fabric.get('trm_enable'):
                            if child_fabric_attributes['ENABLE_TRM'] == 'false':
                                error_msg = (
                                    f"For fabric {child_fabric}; TRM is not enabled in the fabric settings. "
                                    "To enable TRM in VRF, you need to first enable it in the fabric settings."
                                )
                                display.error(error_msg)
                                results['failed'] = True
                                results['msg'] = error_msg
                                return results

                        # Need to check data model and support for enabling TRMv6 in the fabric settings
                        # if vrf.get('trm_enable'):
                        #     if child_fabric_attributes['ENABLE_TRMv6'] == 'false':
                        #         error_msg = (
                        #             f"For fabric {child_fabric}; TRMv6 is not enabled in the fabric settings. "
                        #             "To enable TRMv6 in VRF, you need to first enable it in the fabric settings."
                        #         )
                        #         display.error(error_msg)
                        #         results['failed'] = True
                        #         results['msg'] = error_msg
                        #         return results

                        ndfc_vrf = self._execute_module(
                            module_name=rest_module,
                            module_args={
                                "method": "GET",
                                "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/{child_fabric}/vrfs/{vrf['name']}"
                            },
                            task_vars=task_vars,
                            tmp=tmp
                        )

                        ndfc_vrf_response_data = ndfc_vrf['response']['DATA']
                        ndfc_vrf_template_config = json.loads(ndfc_vrf_response_data['vrfTemplateConfig'])

                        # Check for differences between the data model and the template config from NDFC for the
                        # attributes that are configurable by the user in a child fabric.
                        # Note: This excludes IPv6 related attributes at this time as they are not yet supported fully in the data model.
                        diff_found = False
                        for template_key, map_info in VRF_TEMPLATE_CONFIG_MAP.items():
                            dm_key = map_info['dm_key']
                            default = map_info['default']
                            template_value = ndfc_vrf_template_config.get(template_key, default)
                            dm_value = vrf_child_fabric.get(dm_key, default)
                            # Normalize boolean/string values for comparison
                            if isinstance(default, bool):
                                template_value = str(template_value).lower()
                                dm_value = str(dm_value).lower()
                            if template_value != dm_value:
                                diff_found = True
                                break

                        if diff_found:
                            results['child_fabrics_changed'].append(child_fabric)

                            # Combine task_vars with local_vars for template rendering
                            vrf_vars = {}
                            # vrf_vars.update({'vrf_vars': {}})
                            vrf_vars.update({'fabric_name': ndfc_vrf_response_data['fabric']})
                            # vrf_vars['vrf_vars'] = {**vrf, **ndfc_vrf_vrf_template_config}
                            vrf_vars.update(
                                {
                                    'ndfc': ndfc_vrf_template_config,
                                    'dm': vrf_child_fabric
                                },
                            )

                            # Attempt to find and read the template file
                            role_path = task_vars.get('role_path')
                            version = '3.2'
                            if version_compare(nd_major_minor_patch, '3.1.1', '<='):
                                version = '3.1'
                            template_path = f"{role_path}{MSD_CHILD_FABRIC_VRF_TEMPLATE_PATH}{version}{MSD_CHILD_FABRIC_VRF_TEMPLATE}"

                            try:
                                template_full_path = self._find_needle('templates', template_path)
                                with open(template_full_path, 'r') as template_file:
                                    template_content = template_file.read()
                            except (IOError, AnsibleFileNotFound) as e:
                                return {'failed': True, 'msg': f"Template file not found or unreadable: {str(e)}"}

                            # Create a Templar instance
                            templar = Templar(loader=self._loader, variables=vrf_vars)

                            # Render the template with the combined variables
                            rendered_content = templar.template(template_content)
                            rendered_to_nice_json = templar.environment.filters['to_nice_json'](rendered_content)

                            ndfc_vrf_update = self._execute_module(
                                module_name=rest_module,
                                module_args={
                                    "method": "PUT",
                                    "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/{child_fabric}/vrfs/{vrf['name']}",
                                    "data": rendered_to_nice_json
                                },
                                task_vars=task_vars,
                                tmp=tmp
                            )

                            # Successful response:
                            # {
                            #     "changed": false,
                            #     "response": {
                            #         "RETURN_CODE": 200,
                            #         "METHOD": "PUT",
                            #         "REQUEST_PATH": "https://10.15.0.110:443/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/nac-fabric1/vrfs/NaC-VRF01", # noqa: E501
                            #         "MESSAGE": "OK",
                            #         "DATA": {
                            #         }
                            #     },
                            #     "invocation": {
                            #         "module_args": {
                            #             "method": "PUT",
                            #             "path": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/nac-fabric1/vrfs/NaC-VRF01", # noqa: E501
                            #             "data": "{\n    \"displayName\": \"NaC-VRF01\",\n    \"fabric\": \"nac-fabric1\",\n    \"hierarchicalKey\": \"nac-fabric1\",\n    \"vrfExtensionTemplate\": \"Default_VRF_Extension_Universal\",\n    \"vrfId\": \"150001\",\n    \"vrfName\": \"NaC-VRF01\",\n    \"vrfTemplate\": \"Default_VRF_Universal\",\n    \"vrfTemplateConfig\": \"{\\'asn\\': \\'65001\\', \\'nveId\\': \\'1\\', \\'vrfName\\': \\'NaC-VRF01\\', \\'vrfSegmentId\\': \\'150001\\', \\'vrfVlanId\\': \\'2001\\', \\'vrfVlanName\\': \\'\\', \\'vrfDescription\\': \\'Configured by Ansible NetAsCode\\', \\'vrfIntfDescription\\': \\'Configured by Ansible NetAsCode\\', \\'mtu\\': \\'9216\\', \\'tag\\': \\'12345\\', \\'vrfRouteMap\\': \\'FABRIC-RMAP-REDIST-SUBNET\\', \\'v6VrfRouteMap\\': \\'\\', \\'maxBgpPaths\\': \\'1\\', \\'maxIbgpPaths\\': \\'2\\', \\'ipv6LinkLocalFlag\\': \\'true\\', \\'enableL3VniNoVlan\\': \\'false\\', \\'enableBgpBestPathEcmp\\': \\'false\\', \\'advertiseHostRouteFlag\\': \\'false\\', \\'advertiseDefaultRouteFlag\\': \\'true\\', \\'configureStaticDefaultRouteFlag\\': \\'true\\', \\'bgpPassword\\': \\'\\', \\'bgpPasswordKeyType\\': \\'3\\', \\'ENABLE_NETFLOW\\': \\'false\\', \\'NETFLOW_MONITOR\\': \\'\\', \\'trmEnabled\\': True, \\'loopbackNumber\\': 1002, \\'rpAddress\\': \\'100.100.100.1\\', \\'isRPAbsent\\': False, \\'isRPExternal\\': False, \\'L3VniMcastGroup\\': \\'239.1.1.0\\', \\'multicastGroup\\': \\'224.0.0.0/4\\', \\'trmV6Enabled\\': \\'false\\', \\'rpV6Address\\': \\'\\', \\'isV6RPAbsent\\': \\'false\\', \\'isV6RPExternal\\': \\'false\\', \\'ipv6MulticastGroup\\': \\'\\', \\'disableRtAuto\\': \\'false\\', \\'routeTargetImport\\': \\'\\', \\'routeTargetExport\\': \\'\\', \\'routeTargetImportEvpn\\': \\'\\', \\'routeTargetExportEvpn\\': \\'\\', \\'routeTargetImportMvpn\\': \\'\\', \\'routeTargetExportMvpn\\': \\'\\', \\'mvpnInterAs\\': \\'false\\', \\'trmBGWMSiteEnabled\\': True}\",\n    \"vrfVlanId\": \"2001\"\n}" # noqa: E501
                            #         }
                            #     },
                            #     "_ansible_parsed": true
                            # }
                            if ndfc_vrf_update.get('response'):
                                if ndfc_vrf_update['response']['RETURN_CODE'] == 200:
                                    results['changed'] = True

                            # Failed response:
                            # {
                            #     "failed": true,
                            #     "msg":{
                            #         "RETURN_CODE": 400,
                            #         "METHOD": "PUT",
                            #         "REQUEST_PATH": "https://10.15.0.110:443/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/nac-fabric2/vrfs/NaC-VRF01", # noqa: E501
                            #         "MESSAGE": "Bad Request",
                            #         "DATA": {
                            #             "path": "/rest/top-down/fabrics/nac-fabric2/vrfs/NaC-VRF01",
                            #             "Error": "Bad Request Error",
                            #             "message": "TRM is not enabled in the fabric settings. To enable TRM in VRF, you need to first enable it in the fabric settings.", # noqa: E501
                            #             "timestamp": "2025-02-24 13:49:41.024",
                            #             "status": "400"
                            #         }
                            #     },
                            #     "invocation": {
                            #         "module_args": {
                            #             "method": "PUT",
                            #             "path": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/nac-fabric2/vrfs/NaC-VRF01", # noqa: E501
                            #             "data": "{\n    \"displayName\": \"NaC-VRF01\",\n    \"fabric\": \"nac-fabric2\",\n    \"hierarchicalKey\": \"nac-fabric2\",\n    \"vrfExtensionTemplate\": \"Default_VRF_Extension_Universal\",\n    \"vrfId\": \"150001\",\n    \"vrfName\": \"NaC-VRF01\",\n    \"vrfTemplate\": \"Default_VRF_Universal\",\n    \"vrfTemplateConfig\": \"{\\'asn\\': \\'65002\\', \\'nveId\\': \\'1\\', \\'vrfName\\': \\'NaC-VRF01\\', \\'vrfSegmentId\\': \\'150001\\', \\'vrfVlanId\\': \\'2001\\', \\'vrfVlanName\\': \\'\\', \\'vrfDescription\\': \\'Configured by Ansible NetAsCode\\', \\'vrfIntfDescription\\': \\'Configured by Ansible NetAsCode\\', \\'mtu\\': \\'9216\\', \\'tag\\': \\'12345\\', \\'vrfRouteMap\\': \\'FABRIC-RMAP-REDIST-SUBNET\\', \\'v6VrfRouteMap\\': \\'\\', \\'maxBgpPaths\\': \\'1\\', \\'maxIbgpPaths\\': \\'2\\', \\'ipv6LinkLocalFlag\\': \\'true\\', \\'enableL3VniNoVlan\\': \\'false\\', \\'enableBgpBestPathEcmp\\': \\'false\\', \\'advertiseHostRouteFlag\\': \\'false\\', \\'advertiseDefaultRouteFlag\\': \\'true\\', \\'configureStaticDefaultRouteFlag\\': \\'true\\', \\'bgpPassword\\': \\'\\', \\'bgpPasswordKeyType\\': \\'3\\', \\'ENABLE_NETFLOW\\': \\'false\\', \\'NETFLOW_MONITOR\\': \\'\\', \\'trmEnabled\\': True, \\'loopbackNumber\\': 1002, \\'rpAddress\\': \\'100.100.100.1\\', \\'isRPAbsent\\': False, \\'isRPExternal\\': False, \\'L3VniMcastGroup\\': \\'239.1.1.0\\', \\'multicastGroup\\': \\'224.0.0.0/4\\', \\'trmV6Enabled\\': \\'false\\', \\'rpV6Address\\': \\'\\', \\'isV6RPAbsent\\': \\'false\\', \\'isV6RPExternal\\': \\'false\\', \\'ipv6MulticastGroup\\': \\'\\', \\'disableRtAuto\\': \\'false\\', \\'routeTargetImport\\': \\'\\', \\'routeTargetExport\\': \\'\\', \\'routeTargetImportEvpn\\': \\'\\', \\'routeTargetExportEvpn\\': \\'\\', \\'routeTargetImportMvpn\\': \\'\\', \\'routeTargetExportMvpn\\': \\'\\', \\'mvpnInterAs\\': \\'false\\', \\'trmBGWMSiteEnabled\\': True}\",\n    \"vrfVlanId\": \"2001\"\n}" # noqa: E501
                            #         }
                            #     },
                            #     "_ansible_parsed": true
                            # }
                            if ndfc_vrf_update.get('msg'):
                                if ndfc_vrf_update['msg']['RETURN_CODE'] != 200:
                                    results['failed'] = True
                                    results['msg'] = f"For fabric {child_fabric} and VRF {vrf['name']}; {ndfc_vrf_update['msg']['DATA']['message']}"

        return results

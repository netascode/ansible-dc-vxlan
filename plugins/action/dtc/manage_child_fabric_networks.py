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


import re
import json

display = Display()

# Path to Jinja template files relative to create role
MSD_CHILD_FABRIC_NETWORK_TEMPLATE_PATH = "/../common/templates/ndfc_networks/msd_fabric/child_fabric/"
MSD_CHILD_FABRIC_NETWORK_TEMPLATE = "/msd_child_fabric_network.j2"

# Currently supported Network template config keys and their mapping to data model keys
NETWORK_TEMPLATE_CONFIG_MAP = {
    'loopbackId': {'dm_key': 'dhcp_loopback_id', 'default': ''},
    'ENABLE_NETFLOW': {'dm_key': 'netflow_enable', 'default': False},
    'VLAN_NETFLOW_MONITOR': {'dm_key': 'vlan_netflow_monitor', 'default': ''},
    'trmEnabled': {'dm_key': 'trm_enable', 'default': False},
    'mcastGroup': {'dm_key': 'multicast_group_address', 'default': '239.1.1.1'},
    'enableL3OnBorder': {'dm_key': 'l3gw_on_border', 'default': False},
}


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['changed'] = False
        results['failed'] = False
        results['child_fabrics_changed'] = []

        nd_version = self._task.args["nd_version"]
        msite_data = self._task.args["msite_data"]
        net_config = self._task.args.get("net_config")

        # Extract net_name values from net_config list of dicts
        # net_config contains network(s) to be updated.
        net_names = [item.get('net_name') for item in net_config] if net_config else []

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

        networks = msite_data['overlay_attach_groups']['networks']

        child_fabrics = msite_data['child_fabrics_data']

        for network in networks:

            # Skip network if its name is not in net_names list
            # This reduce iteration to all networks x child_fabrics.
            if network['name'] not in net_names:
                continue

            network_child_fabrics = network.get('child_fabrics', [])

            for child_fabric in child_fabrics.keys():
                # Need to get the child fabric type and ensure it is a VXLAN fabric type
                # Checking for VXLAN fabric type rules out the possibility of a child fabric being an External or other type of fabric type
                child_fabric_type = child_fabrics[child_fabric]['type']
                if child_fabric_type in ['Switch_Fabric']:
                    child_fabric_attributes = child_fabrics[child_fabric]['attributes']

                    network_child_fabric = []
                    if network_child_fabrics:
                        network_child_fabric = [
                            network_child_fabric_dict
                            for network_child_fabric_dict in network_child_fabrics
                            if (network_child_fabric_dict['name'] == child_fabric)
                        ]

                    if len(network_child_fabric) == 0:
                        # There are no matching child fabrics for this Network.
                        # Set network_child_fabric to empty dict for further processing.
                        network_child_fabric = {}
                    elif len(network_child_fabric) == 1:
                        network_child_fabric = network_child_fabric[0]

                    # Need to clean these up and make them more dynamic
                    # Check if fabric settings are properly enabled
                    if network_child_fabric.get('netflow_enable'):
                        if child_fabric_attributes['ENABLE_NETFLOW'] == 'false':
                            error_msg = (
                                f"For fabric {child_fabric}; NetFlow is not enabled in the fabric settings. "
                                "To enable NetFlow in Network, you need to first enable it in the fabric settings."
                            )
                            display.error(error_msg)
                            results['failed'] = True
                            results['msg'] = error_msg
                            return results

                    if network_child_fabric.get('trm_enable'):
                        if child_fabric_attributes['ENABLE_TRM'] == 'false':
                            error_msg = (
                                f"For fabric {child_fabric}; TRM is not enabled in the fabric settings. "
                                "To enable TRM in Network, you need to first enable it in the fabric settings."
                            )
                            display.error(error_msg)
                            results['failed'] = True
                            results['msg'] = error_msg
                            return results

                    # Need to check data model and support for enabling TRMv6 in the fabric settings
                    # if network.get('trm_enable'):
                    #     if child_fabric_attributes['ENABLE_TRMv6'] == 'false':
                    #         error_msg = (
                    #             f"For fabric {child_fabric}; TRMv6 is not enabled in the fabric settings. "
                    #             "To enable TRMv6 in Network, you need to first enable it in the fabric settings."
                    #         )
                    #         display.error(error_msg)
                    #         results['failed'] = True
                    #         results['msg'] = error_msg
                    #         return results

                    ndfc_net = self._execute_module(
                        module_name="cisco.dcnm.dcnm_rest",
                        module_args={
                            "method": "GET",
                            "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/{child_fabric}/networks/{network['name']}",
                        },
                        task_vars=task_vars,
                        tmp=tmp
                    )

                    ndfc_net_response_data = ndfc_net['response']['DATA']
                    ndfc_net_template_config = json.loads(ndfc_net_response_data['networkTemplateConfig'])

                    # Check for differences between the data model and the template config from NDFC for the
                    # attributes that are configurable by the user in a child fabric.
                    # Note: This excludes IPv6 related attributes at this time as they are not yet supported fully in the data model.
                    diff_found = False
                    for ndfc_key, map_info in NETWORK_TEMPLATE_CONFIG_MAP.items():
                        dm_key = map_info['dm_key']
                        default = map_info['default']
                        ndfc_value = ndfc_net_template_config.get(ndfc_key, default)
                        dm_value = network_child_fabric.get(dm_key, default)
                        # Normalize boolean/string values for comparison
                        if isinstance(default, bool):
                            ndfc_value = str(ndfc_value).lower()
                            dm_value = str(dm_value).lower()
                        if ndfc_value != dm_value:
                            diff_found = True
                            break

                    if diff_found:
                        results['child_fabrics_changed'].append(child_fabric)

                        # Combine task_vars with local_vars for template rendering
                        net_vars = {}
                        net_vars.update({'fabric_name': ndfc_net_response_data['fabric']})
                        net_vars.update({'network_name': ndfc_net_response_data['networkName']})
                        net_vars.update(
                            {
                                'ndfc': ndfc_net_template_config,
                                'dm': network_child_fabric
                            },
                        )

                        # Attempt to find and read the template file
                        role_path = task_vars.get('role_path')
                        version = '3.2'
                        if version_compare(nd_major_minor_patch, '3.1.1', '<='):
                            version = '3.1'
                        elif version_compare(nd_major_minor_patch, '4.1.1', '>='):
                            version = '4.1'
                        template_path = f"{role_path}{MSD_CHILD_FABRIC_NETWORK_TEMPLATE_PATH}{version}{MSD_CHILD_FABRIC_NETWORK_TEMPLATE}"

                        try:
                            template_full_path = self._find_needle('templates', template_path)
                            with open(template_full_path, 'r') as template_file:
                                template_content = template_file.read()
                        except (IOError, AnsibleFileNotFound) as e:
                            return {'failed': True, 'msg': f"Template file not found or unreadable: {str(e)}"}

                        # Create a Templar instance
                        templar = Templar(loader=self._loader, variables=net_vars)

                        # Render the template with the combined variables
                        rendered_content = templar.template(template_content)
                        rendered_to_nice_json = templar.environment.filters['to_nice_json'](rendered_content)

                        ndfc_net_update = self._execute_module(
                            module_name="cisco.dcnm.dcnm_rest",
                            module_args={
                                "method": "PUT",
                                "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/{child_fabric}/networks/{network['name']}",
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
                        #         "REQUEST_PATH": "https://10.15.0.110:443/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/nac-fabric1/networks/NaC-Net01", # noqa: E501
                        #         "MESSAGE": "OK",
                        #         "DATA": {
                        #         }
                        #     },
                        #     "invocation": {
                        #         "module_args": {
                        #         "method": "PUT",
                        #         "path": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/nac-fabric1/networks/NaC-Net01", # noqa: E501
                        #         "data": "{\n    \"displayName\": \"NaC-Net01\",\n    \"fabric\": \"nac-fabric1\",\n    \"hierarchicalKey\": \"nac-fabric1\",\n    \"networkExtensionTemplate\": \"Default_Network_Extension_Universal\",\n    \"networkId\": \"130001\",\n    \"networkName\": \"NaC-Net01\",\n    \"networkTemplate\": \"Default_Network_Universal\",\n    \"networkTemplateConfig\": \" {\\'vrfName\\': \\'NaC-VRF01\\', \\'networkName\\': \\'NaC-Net01\\', \\'vlanId\\': \\'2301\\', \\'vlanName\\': \\'NaC-Net01_vlan2301\\', \\'segmentId\\': \\'130001\\', \\'intfDescription\\': \\'Configured by Ansible NetAsCode\\', \\'gatewayIpAddress\\': \\'192.168.1.1/24\\', \\'gatewayIpV6Address\\': \\'\\', \\'mtu\\': \\'9216\\', \\'isLayer2Only\\': \\'false\\', \\'suppressArp\\': \\'false\\', \\'mcastGroup\\': \\'239.1.1.1\\', \\'tag\\': \\'12345\\', \\'secondaryGW1\\': \\'\\', \\'secondaryGW2\\': \\'\\', \\'secondaryGW3\\': \\'\\', \\'secondaryGW4\\': \\'\\', \\'loopbackId\\': \\'\\', \\'dhcpServerAddr1\\': \\'\\', \\'vrfDhcp\\': \\'\\', \\'dhcpServerAddr2\\': \\'\\', \\'vrfDhcp2\\': \\'\\', \\'dhcpServerAddr3\\': \\'\\', \\'vrfDhcp3\\': \\'\\', \\'ENABLE_NETFLOW\\': \\'false\\', \\'SVI_NETFLOW_MONITOR\\': \\'\\', \\'VLAN_NETFLOW_MONITOR\\': \\'\\', \\'enableIR\\': \\'false\\', \\'trmEnabled\\': True, \\'igmpVersion\\': \\'2\\', \\'trmV6Enabled\\': \\'\\', \\'rtBothAuto\\': \\'false\\', \\'enableL3OnBorder\\': \\'false\\', \\'enableL3OnBorderVpcBgw\\': \\'false\\', \\'nveId\\': \\'1\\', \\'type\\': \\'Normal\\'}\",\n    \"type\": \"Normal\",\n    \"vrf\": \"NaC-VRF01\"\n}" # noqa: E501
                        #         }
                        #     },
                        #     "_ansible_parsed": true
                        # }
                        if ndfc_net_update.get('response'):
                            if ndfc_net_update['response']['RETURN_CODE'] == 200:
                                results['changed'] = True

                        # Failed response:
                        # {
                        #     "failed": true,
                        #     "msg": {
                        #         "RETURN_CODE": 500,
                        #         "METHOD": "PUT",
                        #         "REQUEST_PATH": "https://10.15.0.110:443/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/nac-fabric1/networks/NaC-Net01", # noqa: E501
                        #         "MESSAGE": "Internal Server Error",
                        #         "DATA": {
                        #             "path": "/rest/top-down/fabrics/nac-fabric1/networks/NaC-Net01",
                        #             "Error": "Internal Server Error",
                        #             "message": "Netflow not enabled in Fabric Settings",
                        #             "timestamp": "2025-02-25 21:54:26.633",
                        #             "status": "500"
                        #         }
                        #     },
                        #     "invocation": {
                        #         "module_args": {
                        #             "method": "PUT",
                        #             "path": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/nac-fabric1/networks/NaC-Net01", # noqa: E501
                        #             "data": "{\n    \"displayName\": \"NaC-Net01\",\n    \"fabric\": \"nac-fabric1\",\n    \"hierarchicalKey\": \"nac-fabric1\",\n    \"networkExtensionTemplate\": \"Default_Network_Extension_Universal\",\n    \"networkId\": \"130001\",\n    \"networkName\": \"NaC-Net01\",\n    \"networkTemplate\": \"Default_Network_Universal\",\n    \"networkTemplateConfig\": \" {\\'vrfName\\': \\'NaC-VRF01\\', \\'networkName\\': \\'NaC-Net01\\', \\'vlanId\\': \\'2301\\', \\'vlanName\\': \\'NaC-Net01_vlan2301\\', \\'segmentId\\': \\'130001\\', \\'intfDescription\\': \\'Configured by Ansible NetAsCode\\', \\'gatewayIpAddress\\': \\'192.168.1.1/24\\', \\'gatewayIpV6Address\\': \\'\\', \\'mtu\\': \\'9216\\', \\'isLayer2Only\\': \\'false\\', \\'suppressArp\\': \\'false\\', \\'mcastGroup\\': \\'239.1.1.1\\', \\'tag\\': \\'12345\\', \\'secondaryGW1\\': \\'\\', \\'secondaryGW2\\': \\'\\', \\'secondaryGW3\\': \\'\\', \\'secondaryGW4\\': \\'\\', \\'loopbackId\\': \\'\\', \\'dhcpServerAddr1\\': \\'\\', \\'vrfDhcp\\': \\'\\', \\'dhcpServerAddr2\\': \\'\\', \\'vrfDhcp2\\': \\'\\', \\'dhcpServerAddr3\\': \\'\\', \\'vrfDhcp3\\': \\'\\', \\'ENABLE_NETFLOW\\': True, \\'SVI_NETFLOW_MONITOR\\': \\'\\', \\'VLAN_NETFLOW_MONITOR\\': \\'blah\\', \\'enableIR\\': \\'false\\', \\'trmEnabled\\': True, \\'igmpVersion\\': \\'2\\', \\'trmV6Enabled\\': \\'\\', \\'rtBothAuto\\': \\'false\\', \\'enableL3OnBorder\\': \\'false\\', \\'enableL3OnBorderVpcBgw\\': \\'false\\', \\'nveId\\': \\'1\\', \\'type\\': \\'Normal\\'}\",\n    \"type\": \"Normal\",\n    \"vrf\": \"NaC-VRF01\"\n}" # noqa: E501
                        #         }
                        #     },
                        #     "_ansible_parsed": true
                        # }
                        if ndfc_net_update.get('msg'):
                            if ndfc_net_update['msg']['RETURN_CODE'] != 200:
                                results['failed'] = True
                                results['msg'] = f"For fabric {child_fabric}; {ndfc_net_update['msg']['DATA']['message']}"
                                return results

        for child_fabric in child_fabrics.keys():
            # Need to get the child fabric type and ensure it is a VXLAN fabric type
            child_fabric_type = child_fabrics[child_fabric]['type']
            if child_fabric_type in ['Switch_Fabric']:
                # Only process child fabrics that have not already been marked as changed
                if child_fabric not in results['child_fabrics_changed']:
                    # cf = child_fabrics
                    ndfc_cf_nets = self._execute_module(
                        module_name="cisco.dcnm.dcnm_rest",
                        module_args={
                            "method": "GET",
                            "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/{child_fabric}/networks"
                        },
                        task_vars=task_vars,
                        tmp=tmp
                    )

                    ndfc_cf_nets_response_data = ndfc_cf_nets['response']['DATA']

                    for ndfc_net in ndfc_cf_nets_response_data:
                        if ndfc_net['networkStatus'] not in ['NA', 'SUCCESS', 'IN-SYNC', 'DEPLOYED']:
                            results['child_fabrics_changed'].append(child_fabric)

        return results

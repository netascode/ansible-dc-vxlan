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


import json

display = Display()

# Path to Jinja template files relative to create role
MSD_CHILD_FABRIC_VRF_TEMPLATE_CONFIG = "/../common/templates/ndfc_vrfs/msd_fabric/child_fabric/msd_child_fabric_vrf_template_config.j2"
MSD_CHILD_FABRIC_VRF_TEMPLATE = "/../common/templates/ndfc_vrfs/msd_fabric/child_fabric/msd_child_fabric_vrf.j2"


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['changed'] = False
        results['failed'] = False

        msite_data = self._task.args["msite_data"]

        vrfs = msite_data['overlay_attach_groups']['vrfs']
        vrf_attach_groups_dict = msite_data['overlay_attach_groups']['vrf_attach_groups']

        child_fabrics = msite_data['child_fabrics_data']

        for vrf in vrfs:
            vrf_attach_group_switches = [vrf_attach_group_dict['switches'] for vrf_attach_group_dict in vrf_attach_groups_dict if vrf_attach_group_dict['name'] == vrf['vrf_attach_group']][0]
            vrf_attach_group_switches_mgmt_ip_addresses = [vrf_attach_group_switch['mgmt_ip_address'] for vrf_attach_group_switch in vrf_attach_group_switches]

            for child_fabric in child_fabrics.keys():
                child_fabric_attributes = child_fabrics[child_fabric]['attributes']
                # child_fabrics['nac-fabric1']['attributes']['ENABLE_TRM']
                child_fabric_switches = child_fabrics[child_fabric]['switches']
                # child_fabrics['nac-fabric1']['switches']
                child_fabric_switches_mgmt_ip_addresses = [child_fabric_switch['mgmt_ip_address'] for child_fabric_switch in child_fabric_switches]

                is_intersection = set(vrf_attach_group_switches_mgmt_ip_addresses).intersection(set(child_fabric_switches_mgmt_ip_addresses))

                # import epdb; epdb.st()

                if is_intersection:
                    # Need to clean these up and make them more dynamic
                    if vrf.get('netflow_enable'):
                        if child_fabric_attributes['ENABLE_NETFLOW'] == 'false':
                            display.error(f"For fabric {child_fabric}; NetFlow is not enabled in the fabric settings. To enable NetFlow in VRF, you need to first enable it in the fabric settings.")
                            results['failed'] = True
                            results['msg'] = f"For fabric {child_fabric}; NetFlow is not enabled in the fabric settings. To enable NetFlow in VRF, you need to first enable it in the fabric settings."
                            return results

                    if vrf.get('trm_enable'):
                        if child_fabric_attributes['ENABLE_TRM'] == 'false':
                            display.error(f"For fabric {child_fabric}; TRM is not enabled in the fabric settings. To enable TRM in VRF, you need to first enable it in the fabric settings.")
                            results['failed'] = True
                            results['msg'] = f"For fabric {child_fabric}; TRM is not enabled in the fabric settings. To enable TRM in VRF, you need to first enable it in the fabric settings."
                            return results

                    # Need to check data model and support for enabling TRMv6 in the fabric settings
                    # if vrf.get('trm_enable'):
                    #     if child_fabric_attributes['ENABLE_TRMv6'] == 'false':
                    #         # Ansible Display failure
                    #         display.error(f"For fabric {child_fabric}; TRMv6 is not enabled in the fabric settings. To enable TRMv6 in VRF, you need to first enable it in the fabric settings.")
                    #         results['failed'] = True
                    #         results['msg'] = f"For fabric {child_fabric}; TRMv6 is not enabled in the fabric settings. To enable TRMv6 in VRF, you need to first enable it in the fabric settings."

                    ndfc_vrf = self._execute_module(
                        module_name="cisco.dcnm.dcnm_rest",
                        module_args={
                            "method": "GET",
                            "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/{child_fabric}/vrfs/{vrf['name']}"
                        },
                        task_vars=task_vars,
                        tmp=tmp
                    )

                    ndfc_vrf_response_data = ndfc_vrf['response']['DATA']
                    ndfc_vrf_vrf_template_config = json.loads(ndfc_vrf_response_data['vrfTemplateConfig'])

                    # Define local variables specific to the action plugin
                    # local_vars = {
                    #     'local_var1': 'value1',
                    #     'local_var2': 'value2',
                    #     # Add more local variables as needed
                    # }
                    existing_vrf_config = ndfc_vrf_vrf_template_config

                    # Combine task_vars with local_vars for template rendering
                    vrf_vars = {}
                    vrf_vars.update({'vrf_vars': {}})
                    vrf_vars['vrf_vars'] = {**vrf, **existing_vrf_config}
                    # vrf_vars['vrf_vars'].update({'current': vrfs})
                    # vrf_vars['vrf_vars'].update({'existing': ndfc_vrf_vrf_template_config})

                    # Define the path to your Jinja template file
                    # template_file = self._task.args.get('src')

                    role_path = task_vars.get('role_path')

                    # template_path = role_path + MSD_CHILD_FABRIC_VRF_TEMPLATE_CONFIG
                    # vrf_template_config_path = role_path + MSD_CHILD_FABRIC_VRF_TEMPLATE_CONFIG
                    # vrf_vars.update({'vrf_template_config_path': vrf_template_config_path})

                    # Load the template content
                    # template_content = self._loader.get_real_file(role_path + MSD_CHILD_FABRIC_VRF_TEMPLATE_CONFIG)

                    # Attempt to find and read the template file
                    # try:
                    #     template_full_path = self._find_needle('templates', template_path)
                    #     with open(template_full_path, 'r') as template_file:
                    #         template_content = template_file.read()
                    # except (IOError, AnsibleFileNotFound) as e:
                    #     return {'failed': True, 'msg': f"Template file not found or unreadable: {str(e)}"}

                    # # Create a Templar instance
                    # templar = Templar(loader=self._loader, variables=vrf_vars)

                    # # Render the template with the combined variables
                    # rendered_content = templar.template(variable=template_content, convert_bare=True, preserve_trailing_newlines=False, escape_backslashes=False, convert_data=False)
                    # json_dict = json.dumps(rendered_content)
                    # escaped_json_string = json_dict.replace('"', '\\"')

                    # rendered_json = templar.environment.filters['to_nice_json'](rendered_content)

                    # json_str = json.dumps(rendered_content)
                    # escaped_json_str = re.sub(r'"', r'\"', json_str)

                    vrf_vars.update({'fabric_name': ndfc_vrf_response_data['fabric']})
                    # vrf_vars.update({'vrf_updated_config_template': rendered_content})

                    template_path = role_path + MSD_CHILD_FABRIC_VRF_TEMPLATE

                    # Attempt to find and read the template file
                    try:
                        template_full_path = self._find_needle('templates', template_path)
                        with open(template_full_path, 'r') as template_file:
                            template_content = template_file.read()
                    except (IOError, AnsibleFileNotFound) as e:
                        return {'failed': True, 'msg': f"Template file not found or unreadable: {str(e)}"}

                    # # Create a Templar instance
                    templar = Templar(loader=self._loader, variables=vrf_vars)

                    # # Render the template with the combined variables
                    rendered_content = templar.template(template_content)
                    # rendered_content = templar.template(variable=template_content, convert_bare=True, preserve_trailing_newlines=False, escape_backslashes=False, convert_data=False)
                    # rendered_json = json.dumps(rendered_content['vrfTemplateConfig'])
                    # escaped_json_string = rendered_json.replace('"', '\\"')
                    # rendered_content['vrfTemplateConfig'] = escaped_json_string
                    rendered_to_nice_json = templar.environment.filters['to_nice_json'](rendered_content)

                    # escaped_json_string = '"' + rendered_json.replace('"', '\\"') + '"'

                    # json_string = json.dumps(rendered_content['vrfTemplateConfig'])
                    # escaped_json_string = json_string.replace('"', '\\"')
                    # final_output = f'"{escaped_json_string}"'

                    # from ansible.plugins.loader import lookup_loader
                    # template_lookup = lookup_loader.get('ansible.builtin.template', loader=self._loader, templar=self._templar)
                    # rendered_content = template_lookup.run([template_path], variables=vrf_vars, task_vars=task_vars)
                    # escaped_string = rendered_content.replace('"', r'\"')

                    ndfc_vrf_update = self._execute_module(
                        module_name="cisco.dcnm.dcnm_rest",
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
                    #         "REQUEST_PATH": "https://10.15.0.110:443/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/nac-fabric1/vrfs/NaC-VRF01",
                    #         "MESSAGE": "OK",
                    #         "DATA": {
                                
                    #         }
                    #     },
                    #     "invocation": {
                    #         "module_args": {
                    #             "method": "PUT",
                    #             "path": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/nac-fabric1/vrfs/NaC-VRF01",
                    #             "data": "{\n    \"displayName\": \"NaC-VRF01\",\n    \"fabric\": \"nac-fabric1\",\n    \"hierarchicalKey\": \"nac-fabric1\",\n    \"vrfExtensionTemplate\": \"Default_VRF_Extension_Universal\",\n    \"vrfId\": \"150001\",\n    \"vrfName\": \"NaC-VRF01\",\n    \"vrfTemplate\": \"Default_VRF_Universal\",\n    \"vrfTemplateConfig\": \"{\\'asn\\': \\'65001\\', \\'nveId\\': \\'1\\', \\'vrfName\\': \\'NaC-VRF01\\', \\'vrfSegmentId\\': \\'150001\\', \\'vrfVlanId\\': \\'2001\\', \\'vrfVlanName\\': \\'\\', \\'vrfDescription\\': \\'Configured by Ansible NetAsCode\\', \\'vrfIntfDescription\\': \\'Configured by Ansible NetAsCode\\', \\'mtu\\': \\'9216\\', \\'tag\\': \\'12345\\', \\'vrfRouteMap\\': \\'FABRIC-RMAP-REDIST-SUBNET\\', \\'v6VrfRouteMap\\': \\'\\', \\'maxBgpPaths\\': \\'1\\', \\'maxIbgpPaths\\': \\'2\\', \\'ipv6LinkLocalFlag\\': \\'true\\', \\'enableL3VniNoVlan\\': \\'false\\', \\'enableBgpBestPathEcmp\\': \\'false\\', \\'advertiseHostRouteFlag\\': \\'false\\', \\'advertiseDefaultRouteFlag\\': \\'true\\', \\'configureStaticDefaultRouteFlag\\': \\'true\\', \\'bgpPassword\\': \\'\\', \\'bgpPasswordKeyType\\': \\'3\\', \\'ENABLE_NETFLOW\\': \\'false\\', \\'NETFLOW_MONITOR\\': \\'\\', \\'trmEnabled\\': True, \\'loopbackNumber\\': 1002, \\'rpAddress\\': \\'100.100.100.1\\', \\'isRPAbsent\\': False, \\'isRPExternal\\': False, \\'L3VniMcastGroup\\': \\'239.1.1.0\\', \\'multicastGroup\\': \\'224.0.0.0/4\\', \\'trmV6Enabled\\': \\'false\\', \\'rpV6Address\\': \\'\\', \\'isV6RPAbsent\\': \\'false\\', \\'isV6RPExternal\\': \\'false\\', \\'ipv6MulticastGroup\\': \\'\\', \\'disableRtAuto\\': \\'false\\', \\'routeTargetImport\\': \\'\\', \\'routeTargetExport\\': \\'\\', \\'routeTargetImportEvpn\\': \\'\\', \\'routeTargetExportEvpn\\': \\'\\', \\'routeTargetImportMvpn\\': \\'\\', \\'routeTargetExportMvpn\\': \\'\\', \\'mvpnInterAs\\': \\'false\\', \\'trmBGWMSiteEnabled\\': True}\",\n    \"vrfVlanId\": \"2001\"\n}"
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
                    #         "REQUEST_PATH": "https://10.15.0.110:443/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/nac-fabric2/vrfs/NaC-VRF01",
                    #         "MESSAGE": "Bad Request",
                    #         "DATA": {
                    #             "path": "/rest/top-down/fabrics/nac-fabric2/vrfs/NaC-VRF01",
                    #             "Error": "Bad Request Error",
                    #             "message": "TRM is not enabled in the fabric settings. To enable TRM in VRF, you need to first enable it in the fabric settings.",
                    #             "timestamp": "2025-02-24 13:49:41.024",
                    #             "status": "400"
                    #         }
                    #     },
                    #     "invocation": {
                    #         "module_args": {
                    #             "method": "PUT",
                    #             "path": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/nac-fabric2/vrfs/NaC-VRF01",
                    #             "data": "{\n    \"displayName\": \"NaC-VRF01\",\n    \"fabric\": \"nac-fabric2\",\n    \"hierarchicalKey\": \"nac-fabric2\",\n    \"vrfExtensionTemplate\": \"Default_VRF_Extension_Universal\",\n    \"vrfId\": \"150001\",\n    \"vrfName\": \"NaC-VRF01\",\n    \"vrfTemplate\": \"Default_VRF_Universal\",\n    \"vrfTemplateConfig\": \"{\\'asn\\': \\'65002\\', \\'nveId\\': \\'1\\', \\'vrfName\\': \\'NaC-VRF01\\', \\'vrfSegmentId\\': \\'150001\\', \\'vrfVlanId\\': \\'2001\\', \\'vrfVlanName\\': \\'\\', \\'vrfDescription\\': \\'Configured by Ansible NetAsCode\\', \\'vrfIntfDescription\\': \\'Configured by Ansible NetAsCode\\', \\'mtu\\': \\'9216\\', \\'tag\\': \\'12345\\', \\'vrfRouteMap\\': \\'FABRIC-RMAP-REDIST-SUBNET\\', \\'v6VrfRouteMap\\': \\'\\', \\'maxBgpPaths\\': \\'1\\', \\'maxIbgpPaths\\': \\'2\\', \\'ipv6LinkLocalFlag\\': \\'true\\', \\'enableL3VniNoVlan\\': \\'false\\', \\'enableBgpBestPathEcmp\\': \\'false\\', \\'advertiseHostRouteFlag\\': \\'false\\', \\'advertiseDefaultRouteFlag\\': \\'true\\', \\'configureStaticDefaultRouteFlag\\': \\'true\\', \\'bgpPassword\\': \\'\\', \\'bgpPasswordKeyType\\': \\'3\\', \\'ENABLE_NETFLOW\\': \\'false\\', \\'NETFLOW_MONITOR\\': \\'\\', \\'trmEnabled\\': True, \\'loopbackNumber\\': 1002, \\'rpAddress\\': \\'100.100.100.1\\', \\'isRPAbsent\\': False, \\'isRPExternal\\': False, \\'L3VniMcastGroup\\': \\'239.1.1.0\\', \\'multicastGroup\\': \\'224.0.0.0/4\\', \\'trmV6Enabled\\': \\'false\\', \\'rpV6Address\\': \\'\\', \\'isV6RPAbsent\\': \\'false\\', \\'isV6RPExternal\\': \\'false\\', \\'ipv6MulticastGroup\\': \\'\\', \\'disableRtAuto\\': \\'false\\', \\'routeTargetImport\\': \\'\\', \\'routeTargetExport\\': \\'\\', \\'routeTargetImportEvpn\\': \\'\\', \\'routeTargetExportEvpn\\': \\'\\', \\'routeTargetImportMvpn\\': \\'\\', \\'routeTargetExportMvpn\\': \\'\\', \\'mvpnInterAs\\': \\'false\\', \\'trmBGWMSiteEnabled\\': True}\",\n    \"vrfVlanId\": \"2001\"\n}"
                    #         }
                    #     },
                    #     "_ansible_parsed": true
                    # }
                    if ndfc_vrf_update.get('msg'):
                        if ndfc_vrf_update['msg']['RETURN_CODE'] != 200:
                            results['failed'] = True
                            results['msg'] = f"For fabric {child_fabric}; {ndfc_vrf_update['msg']['DATA']['message']} Please revisit the configuration data model for fabric {child_fabric} and enable the required feature(s) in the fabric settings."

                    # # Use the file lookup plugin to read the contents of the file
                    # file_content = self._loader.lookup_loader.get('file', loader=self._loader).run([file_path], variables=task_vars)

        return results

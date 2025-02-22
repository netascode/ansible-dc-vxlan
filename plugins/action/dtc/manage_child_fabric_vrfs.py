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

                if is_intersection:
                    if vrf.get('netflow_enable'):
                        if child_fabric_attributes['ENABLE_NETFLOW']:
                            # Ansible Display failure
                            pass

                    if vrf.get('trm_enable'):
                        if child_fabric_attributes['ENABLE_TRM']:
                            # Ansible Display failure
                            pass

                    if vrf.get('trm_enable'):
                        if child_fabric_attributes['ENABLE_TRMv6']:
                            # Ansible Display failure
                            pass

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

                    import epdb; epdb.st()

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

                    # results['changed'] = True

                    # # Use the file lookup plugin to read the contents of the file
                    # file_content = self._loader.lookup_loader.get('file', loader=self._loader).run([file_path], variables=task_vars)

        return results

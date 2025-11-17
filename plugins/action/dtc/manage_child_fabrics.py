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

display = Display()


class ActionModule(ActionBase):
    """
    Action plugin to manage Multisite child fabrics
    in Nexus Dashboard (ND) for MSD and MCFG parent fabrics.
    """
    def __init__(self, *args, **kwargs):
        super(ActionModule, self).__init__(*args, **kwargs)
        self.tmp = None
        self.task_vars = None
        self.parent_fabric = None
        self.parent_fabric_type = None
        self.multisite_operations_map = {
            'MSD': {
                'add': {
                    'method': 'POST',
                    'path': '/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/msdAdd'
                },
                'remove': {
                    'method': 'POST',
                    'path': '/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/msdExit'
                },
                'data_template': '{{"destFabric":"{parent_fabric}","sourceFabric":"{child_fabric}"}}'
            },
            'MCFG': {
                'add': {
                    'method': 'PUT',
                    'path': '/onemanage/appcenter/cisco/ndfc/api/v1/onemanage/fabrics/{parent_fabric}/members',
                },
                'remove': {
                    'method': 'PUT',
                    'path': '/onemanage/appcenter/cisco/ndfc/api/v1/onemanage/fabrics/{parent_fabric}/members',
                },
                'data_template': '{{"clusterName":"{cluster}","fabricName":"{child_fabric}","operation":"{operation}"}}'
            }
        }

    def _render_data_template(self, template, child_fabric, operation):
        """
        Render the data template with the appropriate values.
        """
        if self.parent_fabric_type == 'MSD':
            return template.format(
                parent_fabric=self.parent_fabric,
                child_fabric=child_fabric['name']
            )
        elif self.parent_fabric_type == 'MCFG':
            return template.format(
                cluster=child_fabric['cluster'],
                child_fabric=child_fabric['name'],
                operation=operation
            )

    def _manage_child_fabric_membership(self, method, path, data):
        """
        Manage child fabrics associated with the parent fabric
        in Nexus Dashboard for MSD and MCFG parent fabrics.
        """
        resposne = self._execute_module(
                        module_name="cisco.dcnm.dcnm_rest",
                        module_args={
                            "method": method,
                            "path": path,
                            "json_data": data
                        },
                        task_vars=self.task_vars,
                        tmp=self.tmp
                    )

        return resposne

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['changed'] = False
        results['failed'] = False

        self.task_vars = task_vars
        self.tmp = tmp

        self.parent_fabric = self._task.args['parent_fabric']
        self.parent_fabric_type = self._task.args["parent_fabric_type"]

        child_fabrics = self._task.args['child_fabrics']

        state = self._task.args['state']

        if not self.multisite_operations_map.keys().__contains__(self.parent_fabric_type):
            results['failed'] = True
            results['msg'] = f"Unsupported parent fabric type {self.parent_fabric_type} for fabric {self.parent_fabric}. Supported types are MSD and MCFG."
            return results

        if state == 'present':
            operation = 'add'
            method = self.multisite_operations_map[self.parent_fabric_type][operation]['method']
            path = self.multisite_operations_map[self.parent_fabric_type][operation]['path'].format(parent_fabric=self.parent_fabric)

        if state == 'absent':
            operation = 'remove'
            method = self.multisite_operations_map[self.parent_fabric_type][operation]['method']
            path = self.multisite_operations_map[self.parent_fabric_type][operation]['path'].format(parent_fabric=self.parent_fabric)

        for fabric in child_fabrics:
            data =  self._render_data_template(
                template=self.multisite_operations_map[self.parent_fabric_type]['data_template'],
                child_fabric=fabric,
                operation=operation
            )

            manage_fabric_result = self._manage_child_fabric_membership(method, path, data)

            if manage_fabric_result.get('failed'):
                results['failed'] = True
                results['msg'] = f"{manage_fabric_result['msg']['MESSAGE']}: {manage_fabric_result['msg']['DATA']}"
                break

            results['changed'] = True

        return results

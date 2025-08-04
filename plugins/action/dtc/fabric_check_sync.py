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

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['changed'] = False
        results['failed'] = False

        fabric = self._task.args["fabric"]

        ndfc_response = self._execute_module(
            module_name=task_vars['ansible_network_os_rest'],
            module_args={
                "method": "GET",
                "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/{fabric}/inventory/switchesByFabric",
            },
            task_vars=task_vars,
            tmp=tmp
        )

        if ndfc_response['response'].get('DATA'):
            for switch in ndfc_response['response']['DATA']:
                if switch['ccStatus'] == 'Out-of-Sync':
                    results['changed'] = True
                    break

        return results

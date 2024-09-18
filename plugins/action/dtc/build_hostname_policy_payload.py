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

from ansible.plugins.action import ActionBase


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['changed'] = False

        model_data = self._task.args["model_data"]

        policy_payload = []

        for switch in model_data["vxlan"]["topology"]["switches"]:
            policy_data = self._execute_module(
                module_name="cisco.dcnm.dcnm_rest",
                module_args={
                    "method": "GET",
                    "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/policies/switches/{switch['serial_number']}/SWITCH/SWITCH"
                },
                task_vars=task_vars,
                tmp=tmp
            )
            policy_match = next((item for item in policy_data["response"]["DATA"] if item["templateName"] == "host_11_1"))
            if policy_match["nvPairs"]["SWITCH_NAME"] != switch["name"]:
                policy_match["nvPairs"]["SWITCH_NAME"] = switch["name"]
                policy_payload.append(policy_match)

        if policy_payload:
            results['changed'] = True

        results['policy_payload'] = policy_payload

        return results

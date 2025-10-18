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
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import ndfc_get_switch_policy_using_template


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['changed'] = False

        model_data = self._task.args["model_data"]
        switch_serial_numbers = self._task.args["switch_serial_numbers"]
        template_name = self._task.args["template_name"]

        policy_update = {}

        for switch_serial_number in switch_serial_numbers:
            policy_match = ndfc_get_switch_policy_using_template(
                self=self,
                task_vars=task_vars,
                tmp=tmp,
                switch_serial_number=switch_serial_number,
                template_name=template_name
            )

            dm_switches = []
            if model_data["vxlan"]["fabric"]["type"] in ('VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'):
                dm_switches = model_data["vxlan"]["topology"]["switches"]

            switch_match = next((item for item in dm_switches if item["serial_number"] == switch_serial_number))

            if not policy_match:
                policy = {
                    "nvPairs": {
                        "SWITCH_NAME": switch_match["name"]
                    },
                    "entityName": "SWITCH",
                    "entityType": "SWITCH",
                    "source": "",
                    "priority": "100",
                    "description": "",
                    "templateName": "host_11_1",
                    "serialNumber": switch_serial_number
                }

                # /appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/policies
                # /appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/policies/bulk-create
                nd_policy_add = self._execute_module(
                    module_name="cisco.dcnm.dcnm_rest",
                    module_args={
                        "method": "PUT",
                        "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/policies",
                        "data": policy
                    },
                    task_vars=task_vars,
                    tmp=tmp
                )

                if nd_policy_add.get('response'):
                    if nd_policy_add['response']['RETURN_CODE'] == 200:
                        results['changed'] = True

                if nd_policy_add.get('msg'):
                    if nd_policy_add['msg']['RETURN_CODE'] != 200:
                        results['failed'] = True
                        results['msg'] = f"For switch {switch_match["name"]}; {nd_policy_add['msg']['DATA']['message']}"


            if policy_match:
                if policy_match["nvPairs"]["SWITCH_NAME"] != switch_match["name"]:
                    policy_match["nvPairs"]["SWITCH_NAME"] = switch_match["name"]
                    policy_update.update({switch_serial_number: policy_match})

            if policy_update:
                policy_ids = ",".join([str(value["policyId"]) for key, value in policy_update.items()])

                nd_policy_update = self._execute_module(
                    module_name="cisco.dcnm.dcnm_rest",
                    module_args={
                        "method": "PUT",
                        "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/policies/{policy_ids}/bulk",
                        "data": policy
                    },
                    task_vars=task_vars,
                    tmp=tmp
                )

                if nd_policy_update.get('response'):
                    if nd_policy_update['response']['RETURN_CODE'] == 200:
                        results['changed'] = True

                if nd_policy_update.get('msg'):
                    if nd_policy_update['msg']['RETURN_CODE'] != 200:
                        results['failed'] = True
                        results['msg'] = f"For switch {switch_match["name"]}; {nd_policy_update['msg']['DATA']['message']}"

        return results

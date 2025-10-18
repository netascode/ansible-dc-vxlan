# Copyright (c) 2025 Cisco Systems, Inc. and its affiliates
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

import json

from ansible.plugins.action import ActionBase
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import ndfc_get_switch_policy_using_template


class ActionModule(ActionBase):
    """
    Action plugin to manage switch hostname policy, host_11_1,
    in Nexus Dashboard (ND) through comparison with the desired
    switch name in the data model to switch hostname policy in ND
    if it exists, or create it if it does not exist.
    """
    def __init__(self, *args, **kwargs):
        super(ActionModule, self).__init__(*args, **kwargs)
        self.tmp = None
        self.task_vars = None
        self.results = {}
        # self.policy_add = {}
        self.policy_update = {}

    def _get_switch_policy(self, switch_serial_number, template_name):
        """
        Get switch hostname policy from Nexus Dashboard using
        template name (host_11_1) and switch serial number.
        """
        return ndfc_get_switch_policy_using_template(
            self=self,
            task_vars=self.task_vars,
            tmp=self.tmp,
            switch_serial_number=switch_serial_number,
            template_name=template_name
        )

    def nd_policy_add(self, switch_name, switch_serial_number):
        """
        Add switch hostname policy in Nexus Dashboard.
        """
        policy = {
            "nvPairs": {
                "SWITCH_NAME": switch_name
            },
            "entityName": "SWITCH",
            "entityType": "SWITCH",
            "source": "",
            "priority": "100",
            "description": "",
            "templateName": "host_11_1",
            "serialNumber": switch_serial_number
        }

        nd_policy_add = self._execute_module(
            module_name="cisco.dcnm.dcnm_rest",
            module_args={
                "method": "POST",
                "path": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/policies",
                "data": json.dumps(policy)
            },
            task_vars=self.task_vars,
            tmp=self.tmp
        )

        if nd_policy_add.get('response'):
            if nd_policy_add['response']['RETURN_CODE'] == 200:
                self.results['changed'] = True

        if nd_policy_add.get('msg'):
            if nd_policy_add['msg']['RETURN_CODE'] != 200:
                self.results['failed'] = True
                self.results['msg'] = f"For switch {switch_name} addition; {nd_policy_add['msg']['DATA']['message']}"

    def build_policy_update(self, policy, switch_name, switch_serial_number):
        """
        Build switch hostname policy update data structure.
        """
        policy["nvPairs"]["SWITCH_NAME"] = switch_name
        self.policy_update.update({switch_serial_number: policy})

    def nd_policy_update(self):
        """
        Bulk update switch hostname policy in Nexus Dashboard.
        """
        policy_ids = ",".join([str(value["policyId"]) for key, value in self.policy_update.items()])

        nd_policy_update = self._execute_module(
            module_name="cisco.dcnm.dcnm_rest",
            module_args={
                "method": "PUT",
                "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/policies/{policy_ids}/bulk",
                "data": self.policy_update
            },
            task_vars=self.task_vars,
            tmp=self.tmp
        )

        if nd_policy_update.get('response'):
            if nd_policy_update['response']['RETURN_CODE'] == 200:
                self.results['changed'] = True

        if nd_policy_update.get('msg'):
            if nd_policy_update['msg']['RETURN_CODE'] != 200:
                self.results['failed'] = True
                self.results['msg'] = f"Bulk update failed; {nd_policy_update['msg']['DATA']['message']}"

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['changed'] = False

        self.task_vars = task_vars
        self.tmp = tmp

        model_data = self._task.args["model_data"]
        template_name = self._task.args["template_name"]

        dm_switches = []
        switch_serial_numbers = []
        if model_data["vxlan"]["fabric"]["type"] in ('VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'):
            dm_switches = model_data["vxlan"]["topology"]["switches"]
            switch_serial_numbers = [dm_switch['serial_number'] for dm_switch in dm_switches]

        for switch_serial_number in switch_serial_numbers:
            policy_match = self._get_switch_policy(switch_serial_number, template_name)

            switch_match = next((item for item in dm_switches if item["serial_number"] == switch_serial_number))

            if not policy_match:
                self.nd_policy_add(
                    switch_name=switch_match['name'],
                    switch_serial_number=switch_serial_number
                )

                if self.results['failed']:
                    results['failed'] = self.results['failed']
                    results['msg'] = self.results['msg']
                    return results

                if self.results['changed']:
                    results['changed'] = self.results['changed']

            if policy_match:
                if policy_match["nvPairs"]["SWITCH_NAME"] != switch_match['name']:
                    self.build_policy_update(
                        policy=policy_match,
                        switch_name=switch_match['name'],
                        switch_serial_number=switch_serial_number
                    )

        if self.policy_update:
            self.nd_policy_update()

            if self.results['failed']:
                results['failed'] = self.results['failed']
                results['msg'] = self.results['msg']
                return results

            if self.results['changed']:
                results['changed'] = self.results['changed']

        return results

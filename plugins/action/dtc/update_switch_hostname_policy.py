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
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import (
    ndfc_get_fabric_policies_by_template,
    ndfc_get_switch_policy_using_template
)


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
        self.results['failed'] = False
        self.results['changed'] = False
        self.policy_update = {}
        self.bulk_api_available = True  # Track if bulk API is available

    def _get_policies_with_fallback(self, fabric_name, template_name, switch_serial_numbers):
        """
        Get switch policies using bulk API if available, fallback to per-switch queries.
        
        Returns:
            tuple: (policies_dict, used_bulk_api)
                - policies_dict: Dictionary mapping serial_number to policy data (or None if not found)
                - used_bulk_api: Boolean indicating if bulk API was used
        """
        policies_dict = {}
        
        # Try bulk API first (only if not already marked as unavailable)
        if self.bulk_api_available:
            try:
                policies_dict = ndfc_get_fabric_policies_by_template(
                    self=self,
                    task_vars=self.task_vars,
                    tmp=self.tmp,
                    fabric_name=fabric_name,
                    template_name=template_name
                )
                # If successful, return the bulk result
                return policies_dict, True
            except Exception as e:
                # Bulk API not available or failed, mark it and fall back
                self.bulk_api_available = False
        
        # Fallback: Query each switch individually
        # Note: ndfc_get_switch_policy_using_template handles the host_11_1 special case
        for switch_serial_number in switch_serial_numbers:
            policy = ndfc_get_switch_policy_using_template(
                self=self,
                task_vars=self.task_vars,
                tmp=self.tmp,
                switch_serial_number=switch_serial_number,
                template_name=template_name
            )
            policies_dict[switch_serial_number] = policy
        
        return policies_dict, False

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
                "data": json.dumps(list(self.policy_update.values()))
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

        data_model = self._task.args["data_model"]
        template_name = self._task.args["template_name"]

        dm_switches = []
        switch_serial_numbers = []
        if data_model["vxlan"]["fabric"]["type"] in ('VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'):
            dm_switches = data_model["vxlan"]["topology"]["switches"]
            switch_serial_numbers = [dm_switch['serial_number'] for dm_switch in dm_switches]

        # Get policies using bulk API with fallback to per-switch queries
        fabric_name = data_model["vxlan"]["fabric"]["name"]
        policies_dict, used_bulk_api = self._get_policies_with_fallback(
            fabric_name=fabric_name,
            template_name=template_name,
            switch_serial_numbers=switch_serial_numbers
        )

        for switch_serial_number in switch_serial_numbers:
            # Look up policy from the dictionary (bulk or per-switch query)
            policy_match = policies_dict.get(switch_serial_number)

            switch_match = next((item for item in dm_switches if item["serial_number"] == switch_serial_number))

            if not policy_match:
                # If bulk API was used and policy not found for non-host_11_1 template, raise error
                # (per-switch method already handles this via exception in helper function)
                if used_bulk_api and template_name != "host_11_1":
                    err_msg = f"Policy for template {template_name} and switch {switch_serial_number} not found!"
                    err_msg += f" Please ensure switch with serial number {switch_serial_number} is part of the fabric."
                    results['failed'] = True
                    results['msg'] = err_msg
                    return results

                # Policy not found - create it (only for host_11_1 template)
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

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
from ...plugin_utils.helper_functions import ndfc_get_switch_policy_using_desc


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['changed'] = False

        # List of switch serial numbes obtained directly from NDFC
        ndfc_sw_data = self._task.args["switch_data"]
        # Data from data model
        edge_connections = self._task.args.get("edge_connections", [{}])[0].get("switch", [])
        restructured_edge_connections = {}
        # For each switch current_sw_policies will be used to store a list of policies currently associated to the switch
        # For each switch that has unmanaged policies, the switch IP address and the list of unmanaged policies will be stored
        # This default dict is the start of what is required for the NDFC policy module
        unmanaged_edge_connections = [
            {
                "switch": []
            }
        ]
        # Iterate over each item in the data list
        for item in edge_connections:
            ip = item['ip']
            # If the IP is not already a key in the dictionary, add it with an empty list
            if ip not in restructured_edge_connections:
                restructured_edge_connections[ip] = []
            # Iterate over each policy and collect the descriptions
            for policy in item['policies']:
                description = policy['description']
                restructured_edge_connections[ip].append(description)

        # Print the resulting dictionary
        # print(restructured_edge_connections)

        for ndfc_sw in ndfc_sw_data:

            # Check if the serial number from NDFC matches any serial number for a switch in the data model
            # If found, grab the specific switch entry from the data model
            # Also if a match, set the IP mgmt information for the current switch found

            for ip in restructured_edge_connections:
                if ndfc_sw["ipAddress"] == ip:
                    # print(ndfc_sw)
                    # Query NDFC for the current switch's serial number to get back any policy that exists for that switch
                    # with the description prepended with "nace_" or "edge_"
                    # First call with "edge_" prefix for backwards compatibility
                    ndfc_policies_with_edge_desc = ndfc_get_switch_policy_using_desc(self, task_vars, tmp, ndfc_sw["serialNumber"], "edge_")

                    # Second call with new prefix nac edge connection prefix nace_
                    ndfc_policies_with_nac_desc = ndfc_get_switch_policy_using_desc(self, task_vars, tmp, ndfc_sw["serialNumber"], "nace_")

                    # Combine the results from both calls
                    combined_policies = ndfc_policies_with_edge_desc + ndfc_policies_with_nac_desc

                    # Use the combined results in the subsequent logic
                    for policy in combined_policies:
                        if policy['description'] not in restructured_edge_connections[ip]:
                            unmanaged_edge_connections[0]["switch"].append(
                                {
                                    "ip": ip
                                }
                            )
                            # Grab the last index of a switch added
                            last_idx = len(unmanaged_edge_connections[0]["switch"]) - 1
                            # Since initially found there is indeed an unmananged policy, build a list of unmanaged policy
                            _unmanaged_edge_connections = [
                                {
                                    "name": policy["policyId"],
                                    "description": policy["description"]
                                }
                            ]
                            # Update the dictionary entry for the last switch with the expected policies key the NDFC policy module expects
                            unmanaged_edge_connections[0]["switch"][last_idx].update(
                                {
                                    "policies": _unmanaged_edge_connections
                                }
                            )
                # Currently, check two things to determine an unmanaged policy:
                # Check no matching policy in the data model against the policy returned from NDFC for the current switch
                # This check uses the prepended "nac_"
                # Additionally, as of now, check no matching policy is from the VRF Lite policy of the data model
                        # If found, do the following:
                        # Update Ansible result status
                        # Add the switch to unmanaged_policies payload
                        # Get the last index of where the switch was added
                        # Build specific unmanaged policy entry
                        # Add unmanaged policy entry to last switch added to list
                        # Update Ansible for a configuration change
                            results['changed'] = True
                        # Update unmanaged_policies with the IP address of the switch that now has unmanaged policy
                        # The NDFC policy module can take a list of various dictionaries with the switch key previously being pre-stored
                        # Given this, each update the switch element with a new switch entry is the zeroth reference location always in unmanaged_policies
                        # Example:
                        # [
                        #     {
                        #         "switch": [
                        #             {
                        #                 "ip": <mgmt_ip_address>,
                        #             }
                        #         ]
                        #     }
                        # ]
                        # Example of unmanaged policy payload:
                        # [
                        #     {
                        #         "switch": [
                        #             {
                        #                 "ip": '<ip_address>',
                        #                 "policies": [
                        #                     {
                        #                         "name": <Policy ID>,
                        #                         "description": "nac_<description>"
                        #                     },
                        #                     {
                        #                         "name": <Policy ID>,
                        #                         "description": "nac_<description>"
                        #                     },
                        #                 ]
                        #             },
                        #         ]
                        #     }
                        # ]

        # Store the unmanaged policy payload for return and usage in the NDFC policy module to delete from NDFC
        # print(unmanaged_edge_connections)
        results['unmanaged_edge_connections'] = unmanaged_edge_connections

        return results

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
        ndfc_sw_serial_numbers = self._task.args["switch_serial_numbers"]
        # Data from data model
        model_data = self._task.args["model_data"]

        # Switches list from data model
        dm_topology_switches = model_data["vxlan"]["topology"]["switches"]

        # Policy, Poilcy Groups, and Switches Policy Group lists from data model
        dm_policy_policies = model_data["vxlan"]["policy"]["policies"]
        dm_policy_groups = model_data["vxlan"]["policy"]["groups"]
        dm_policy_switches = model_data["vxlan"]["policy"]["switches"]

        # For each switch current_sw_policies will be used to store a list of policies currently associated to the switch
        # For each switch that has unmanaged policies, the switch IP address and the list of unmanaged policies will be stored
        # This default dict is the start of what is required for the NDFC policy module
        unmanaged_policies = [
            {
                "switch": []
            }
        ]

        # Loop over each serial number obtained from NDFC
        for ndfc_sw_serial_number in ndfc_sw_serial_numbers:
            # Set empty default values to reset for each switch
            dm_switch_found = {}
            dm_management_ipv4_address = ""
            dm_management_ipv6_address = ""
            dm_policy_switch = {}
            current_sw_policies = []

            # Check if the serial number from NDFC matches any serial number for a switch in the data model
            # If found, grab the specific switch entry from the data model
            # Also if a match, set the IP mgmt information for the current switch found
            if any(switch["serial_number"] == ndfc_sw_serial_number for switch in dm_topology_switches):
                dm_switch_found = next(
                    (dm_topology_switch for dm_topology_switch in dm_topology_switches if dm_topology_switch["serial_number"] == ndfc_sw_serial_number)
                )
                dm_management_ipv4_address = dm_switch_found["management"].get("management_ipv4_address", None)
                dm_management_ipv6_address = dm_switch_found["management"].get("management_ipv6_address", None)

            # Check if the name matching either the IPv4 or IPv6 mgmt address is found in the policy switches data model
            # If found, grab the specific entry from the policy switches data model and store
            # This stores the current switches policy group list
            if any(
                (switch["mgmt_ip_address"] == dm_management_ipv4_address for switch in dm_policy_switches) or
                (switch["mgmt_ip_address"] == dm_management_ipv6_address for switch in dm_policy_switches)
            ):
                dm_policy_switch = next(
                    (
                        dm_policy_switch for dm_policy_switch in dm_policy_switches
                        if dm_policy_switch["mgmt_ip_address"] == dm_management_ipv4_address or
                        dm_policy_switch["mgmt_ip_address"] == dm_management_ipv6_address
                    )
                )

                # Loop over each policy group associated to the current switch in the data model
                for dm_sw_policy_group in dm_policy_switch["groups"]:
                    # Check if the policy group name associated to the switch is found in the policy groups data model
                    # If found, store a list of current policies that are part of that policy group in the data model
                    # In the process of storing, reformat the policy description name to prepend "nac_" and replace white spaces with underscores
                    if any(dm_policy_group["name"] == dm_sw_policy_group for dm_policy_group in dm_policy_groups):
                        current_sw_policies.extend(
                            next(
                                (
                                    ["nac_" + policy["name"].replace(" ", "_") for policy in dm_policy_group["policies"]]
                                    for dm_policy_group in dm_policy_groups if dm_policy_group["name"] == dm_sw_policy_group
                                )
                            )
                        )

            # Query NDFC for the current switch's serial number to get back any policy that exists for that switch
            # with the description prepended with "nac_"
            ndfc_policies_with_nac_desc = ndfc_get_switch_policy_using_desc(self, task_vars, tmp, ndfc_sw_serial_number, "nac_")

            # Currently, check two things to determine an unmanaged policy:
            # Check no matching policy in the data model against the policy returned from NDFC for the current switch
            # This check uses the prepended "nac_"
            # Additionally, as of now, check no matching policy is from the VRF Lite policy of the data model
            if any(
                (ndfc_policy_with_nac_desc["description"] not in current_sw_policies)
                for ndfc_policy_with_nac_desc in ndfc_policies_with_nac_desc
            ):
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
                unmanaged_policies[0]["switch"].append(
                    {
                        "ip": dm_management_ipv4_address if dm_management_ipv4_address else dm_management_ipv6_address
                    }
                )

                # Grab the last index of a switch added
                last_idx = len(unmanaged_policies[0]["switch"]) - 1

                # Since initially found there is indeed an unmananged policy, build a list of unmanaged policy
                _unmanaged_policies = [
                    {
                        "name": ndfc_policy_with_nac_desc["policyId"],
                        "description": ndfc_policy_with_nac_desc["description"]
                    }
                    for ndfc_policy_with_nac_desc in ndfc_policies_with_nac_desc
                    if (ndfc_policy_with_nac_desc["description"] not in current_sw_policies)
                ]

                # Update the dictionary entry for the last switch with the expected policies key the NDFC policy module expects
                unmanaged_policies[0]["switch"][last_idx].update(
                    {
                        "policies": _unmanaged_policies
                    }
                )

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
        results['unmanaged_policies'] = unmanaged_policies

        return results

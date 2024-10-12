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
from ..helper_functions import ndfc_get_switch_policy_with_desc


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['changed'] = False

        # Switches from NDFC
        ndfc_sw_serial_numbers = self._task.args["switch_serial_numbers"]
        model_data = self._task.args["model_data"]

        dm_topology_switches = model_data["vxlan"]["topology"]["switches"]

        dm_policy_policies = model_data["vxlan"]["policy"]["policies"]
        dm_policy_groups = model_data["vxlan"]["policy"]["groups"]
        dm_policy_switches = model_data["vxlan"]["policy"]["switches"]

        vrf_lites = []
        if model_data["vxlan"].get("overlay_extensions", None):
            if model_data["vxlan"]["overlay_extensions"].get("vrf_lites", None):
                dm_vrf_lites = model_data["vxlan"]["overlay_extensions"]["vrf_lites"]
                for dm_vrf_lite in dm_vrf_lites:
                    for dm_vrf_lite_switch in dm_vrf_lite["switches"]:
                        unique_name = f"nac_{dm_vrf_lite['name']}_{dm_vrf_lite_switch['name']}"
                        vrf_lites.append(unique_name)

        dm_management_ipv4_address = ""
        dm_management_ipv6_address = ""
        current_sw_policies = []
        umanaged_policies = [
            {
                "switch": []
            }
        ]

        for ndfc_sw_serial_number in ndfc_sw_serial_numbers:
            if any(switch["serial_number"] == ndfc_sw_serial_number for switch in dm_topology_switches):
                dm_switch_found = next(
                    (dm_topology_switch for dm_topology_switch in dm_topology_switches if dm_topology_switch["serial_number"] == ndfc_sw_serial_number)
                )
                dm_management_ipv4_address = dm_switch_found["management"].get("management_ipv4_address", None)
                dm_management_ipv6_address = dm_switch_found["management"].get("management_ipv6_address", None)

            if any(
                (switch["name"] == dm_management_ipv4_address for switch in dm_policy_switches) or
                (switch["name"] == dm_management_ipv6_address for switch in dm_policy_switches)
            ):
                dm_policy_switch = next(
                    (
                        dm_policy_switch for dm_policy_switch in dm_policy_switches
                        if dm_policy_switch["name"] == dm_management_ipv4_address or dm_policy_switch["name"] == dm_management_ipv6_address
                    )
                )

                for dm_sw_policy_group in dm_policy_switch["groups"]:
                    if any(dm_policy_group["name"] == dm_sw_policy_group for dm_policy_group in dm_policy_groups):
                        current_sw_policies = next(
                            (
                                [policy["name"] for policy in dm_policy_group["policies"]]
                                for dm_policy_group in dm_policy_groups if dm_policy_group["name"] == dm_sw_policy_group
                            )
                        )

                ndfc_policies_with_desc = ndfc_get_switch_policy_with_desc(self, task_vars, tmp, ndfc_sw_serial_number)
                if any(
                    ((ndfc_policy_with_desc["description"] not in vrf_lites) and (ndfc_policy_with_desc["description"] not in current_sw_policies))
                    for ndfc_policy_with_desc in ndfc_policies_with_desc
                ):
                    results['changed'] = True
                    umanaged_policies[0]["switch"].append(
                        {
                            "ip": dm_management_ipv4_address if dm_management_ipv4_address else dm_management_ipv6_address
                        }
                    )
                    last_idx = len(umanaged_policies[0]["switch"]) - 1
                    _unmanaged_policies = [
                        {
                            "name": ndfc_policy_with_desc["policyId"],
                            "description": ndfc_policy_with_desc["description"]
                        }
                        for ndfc_policy_with_desc in ndfc_policies_with_desc
                        if ((ndfc_policy_with_desc["description"] not in vrf_lites) and (ndfc_policy_with_desc["description"] not in current_sw_policies))
                    ]
                    umanaged_policies[0]["switch"][last_idx].update(
                        {
                            "policies": _unmanaged_policies
                        }
                    )

        results['unmanaged_policies'] = umanaged_policies

        return results

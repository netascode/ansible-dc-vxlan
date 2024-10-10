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
from ..helper_functions import ndfc_get_switch_policy_by_desc


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['changed'] = False

        # Switches from NDFC
        switch_serial_numbers = self._task.args["switch_serial_numbers"]
        model_data = self._task.args["model_data"]

        policy_policies = model_data["vxlan"]["policy"]["policies"]
        policy_groups = model_data["vxlan"]["policy"]["groups"]
        policy_switches = model_data["vxlan"]["policy"]["switches"]

        topology_switches = model_data["vxlan"]["topology"]["switches"]

        policy_update = {}

        for switch_serial_number in switch_serial_numbers:
            import epdb; epdb.st()

            topology_switch = next((item for item in topology_switches if item["serial_number"] == switch_serial_number))
            management_ipv4_address = topology_switch["management"]["management_ipv4_address"]


            policy_switch = next((item for item in policy_switches if item["name"] == management_ipv4_address))

            # if not (
            #     switch["management"].get("management_ipv4_address", False)
            #     or switch["management"].get("management_ipv6_address", False)
            # ):
            #     pass

            # policy_match = ndfc_get_switch_policy_by_desc(
            #     self=self,
            #     task_vars=task_vars,
            #     tmp=tmp,
            #     switch_serial_number=switch_serial_number,
            #     description=description
            # )

        return results

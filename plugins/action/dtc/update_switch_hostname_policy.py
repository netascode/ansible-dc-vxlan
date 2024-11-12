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
from ...plugin_utils.helper_functions import ndfc_get_switch_policy_using_template


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

            switch_match = next((item for item in model_data["vxlan"]["topology"]["switches"] if item["serial_number"] == switch_serial_number))

            if policy_match["nvPairs"]["SWITCH_NAME"] != switch_match["name"]:
                policy_match["nvPairs"]["SWITCH_NAME"] = switch_match["name"]
                policy_update.update({switch_serial_number: policy_match})

        if policy_update:
            results['changed'] = True

        results['policy_update'] = policy_update

        return results

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
import os
import yaml

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        # self._supports_async = True
        results = super(ActionModule, self).run(tmp, task_vars)
        results['diff_run'] = True
        results['validate_only_run'] = False

        model_data = self._task.args.get('model_data')
        play_tags = self._task.args.get('play_tags')
        fabric_name = model_data['vxlan']['fabric']['name']

        if 'dtc' in task_vars['role_path']:
            common_role_path = os.path.dirname(task_vars['role_path'])
            common_role_path = os.path.dirname(common_role_path) + '/validate/files'
        else:
            common_role_path = os.path.dirname(task_vars['role_path']) + '/validate/files'

        run_map_file_path = common_role_path + f'/{fabric_name}_run_map.yml'

        if not os.path.exists(run_map_file_path):
            # Return failure if run_map file does not exist
            results['diff_run'] = False
            return results

        with open(run_map_file_path, 'r') as file:
            previous_run_map = yaml.safe_load(file)

        # Check run map flags and if any of then is false set diff_run to false
        # to force all sections to run.
        # Set diff_run to false for any of the following conditions:
        #   - Any of the runmap flags is false
        #   - play_tags (ansible_run_tags) is something other then 'all'
        #
        for role in ['role_validate_completed', 'role_create_completed', 'role_deploy_completed', 'role_remove_completed']:
            if not previous_run_map.get(role):
                results['diff_run'] = False
                break
        # All stages of the automation must run for the diff_run framework to be enabled
        if play_tags and 'all' not in play_tags:
            results['diff_run'] = False

        # If only the role_validate tag is present then set validate_only_run to true
        # This is used to prevent the diff_run map from being reset when the validate role
        # gets run in isolation.
        if len(play_tags) == 1 and 'role_validate' in play_tags:
            results['validate_only_run'] = True

        # If diff_run is false display an ansible warning message
        if not results['diff_run']:
            display.warning(
                f"Diff Run Feature is Disabled on this run for Fabric {fabric_name} "
                f"as one or more run map flags are `false` or `ansible_run_tags` is not 'all'."
            )

        return results

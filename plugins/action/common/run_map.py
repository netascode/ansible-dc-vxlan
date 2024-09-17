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
from datetime import datetime as dt
import re
import os
import yaml

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        # self._supports_async = True
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False

        model_data = task_vars['model_data']['data']
        stage = self._task.args['stage']
        fabric_name = model_data["vxlan"]["global"]["name"]

        if 'dtc' in task_vars['role_path']:
            common_role_path = os.path.dirname(task_vars['role_path'])
            common_role_path = os.path.dirname(common_role_path) + '/validate/files'
        else:
            common_role_path = os.path.dirname(task_vars['role_path']) + '/validate/files'

        if not os.path.exists(common_role_path):
            # Return failure if the common role path does not exist
            results['failed'] = True

        run_map_file_path = common_role_path + f'/{fabric_name}_run_map.yml'

        if stage == 'starting_execution':
            updated_run_map = {}
            updated_run_map['time_stamp'] = dt.now().isoformat()
            # Using the following string '2024-07-31T09:50:33.098568' as an example
            # create a regsub that will convert '-', '.', and ':' to '_'
            updated_run_map['time_stamp'] = re.sub(r'[-.:]', '_', updated_run_map['time_stamp'])

            updated_run_map['role_validate_completed'] = False
            updated_run_map['role_create_completed'] = False
            updated_run_map['role_deploy_completed'] = False
            updated_run_map['role_remove_completed'] = False

        if stage != 'starting_execution':
            with open(run_map_file_path, 'r') as file:
                data = yaml.safe_load(file)
            updated_run_map = data
            if stage == 'role_validate_completed':
                updated_run_map['role_validate_completed'] = True
            elif stage == 'role_create_completed':
                updated_run_map['role_create_completed'] = True
            elif stage == 'role_deploy_completed':
                updated_run_map['role_deploy_completed'] = True
            elif stage == 'role_remove_completed':
                updated_run_map['role_remove_completed'] = True

        with open(run_map_file_path, 'w') as outfile:
            outfile.write("### This File Is Auto Generated, Do Not Edit ###\n")
            yaml.dump(updated_run_map, outfile, default_flow_style=False)

        return results

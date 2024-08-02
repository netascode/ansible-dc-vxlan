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
        results['diff_run'] = True

        if 'dtc' in task_vars['role_path']:
            common_role_path = os.path.dirname(task_vars['role_path'])
            common_role_path = os.path.dirname(common_role_path) + '/validate/files'
        else:
            common_role_path = os.path.dirname(task_vars['role_path']) + '/validate/files'

        run_map_file_path = common_role_path + '/run_map.yml'

        if not os.path.exists(run_map_file_path):
            # Return failure if run_map file does not exist
            results['diff_run'] = False
            return results

        with open(run_map_file_path, 'r') as file:
            previous_run_map = yaml.safe_load(file)

        # Check run map flags and if all are true then set diff_run to true
        for role in ['role_validate_completed', 'role_create_completed', 'role_deploy_completed', 'role_remove_completed']:
            if not previous_run_map.get(role):
                results['diff_run'] = False
                break

        return results
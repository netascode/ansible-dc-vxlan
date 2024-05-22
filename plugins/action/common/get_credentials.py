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
import copy

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        # self._supports_async = True
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False

        inv_list = self._task.args['inv_list']
        username = task_vars.get('ndfc_device_username')
        password = task_vars.get('ndfc_device_password')

        # Fail if username and password are not set
        if username is None or password is None:
            results['failed'] = True
            results['msg'] = "ndfc_device_username and ndfc_device_username must be set in group_vars or as environment variables!"
            # TODO: Add support for environemnt variables
            return results

        # Create a new list and deep copy each dict item to avoid modifying the original and dict items
        updated_inv_list = []
        for device in inv_list:
            updated_inv_list.append(copy.deepcopy(device))

        for new_device in updated_inv_list:
            new_device['user_name'] = username
            new_device['password'] = password

        results['updated_inv_list'] = updated_inv_list
        return results

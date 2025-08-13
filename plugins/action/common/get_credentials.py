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

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase
import copy
import os

display = Display()


class ActionModule(ActionBase):

    @staticmethod
    def _get_credentials_from_env(var_name):
        """
        Pull credentials from environment variables.
        If not found, return "not_set" strings.
        """
        return os.getenv(var_name, 'not_set')

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['retrieve_failed'] = False

        key_username = 'ndfc_switch_username'
        key_password = 'ndfc_switch_password'

        ndfc_host_name = task_vars['inventory_hostname']
        username = task_vars['hostvars'][ndfc_host_name].get(key_username, '')
        password = task_vars['hostvars'][ndfc_host_name].get(key_password, '')

        # Fail if username and password are not set
        if username == '' or password == '':
            results['retrieve_failed'] = True
            results['msg'] = "{0} and {1} must be set in group_vars or as environment variables!".format(key_username, key_password)
            return results

        inv_list = self._task.args['inv_list']
        # Create a new list and deep copy each dict item to avoid modifying the original and dict items
        updated_inv_list = []
        for device in inv_list:
            updated_inv_list.append(copy.deepcopy(device))
        for new_device in updated_inv_list:
            device_ip = new_device.get('seed_ip', 'unknown')
            inv_list_user_name = new_device.get('user_name')
            inv_list_passw = new_device.get('password')

            # Handle username field
            if inv_list_user_name == 'PLACE_HOLDER_USERNAME':
                new_device['user_name'] = username
            elif inv_list_user_name and inv_list_user_name.startswith('env_var_'):
                # Handle the case where user_name starts with "env_var_"
                env_var_name = inv_list_user_name.replace('env_var_', '', 1)
                credential = self._get_credentials_from_env(env_var_name)
                if credential == 'not_set':
                    display.warning(f"Environment variable '{env_var_name}' not found for device {device_ip}. Using group_vars username.")
                    new_device['user_name'] = username
                else:
                    new_device['user_name'] = credential
            elif inv_list_user_name:
                # Plain text username - security warning
                display.warning(f"Plain text username detected for device {device_ip}. Using plain text credentials in configuration files is not secure.")
            else:
                new_device['user_name'] = username

            # Handle password field
            if inv_list_passw == 'PLACE_HOLDER_PASSWORD':
                new_device['password'] = password
            elif inv_list_passw and inv_list_passw.startswith('env_var_'):
                # Handle the case where password starts with "env_var_"
                env_var_name = inv_list_passw.replace('env_var_', '', 1)
                credential = self._get_credentials_from_env(env_var_name)
                if credential == 'not_set':
                    display.warning(f"Environment variable '{env_var_name}' not found for device {device_ip}. Using group_vars password.")
                    new_device['password'] = password
                else:
                    new_device['password'] = credential
            elif inv_list_passw:
                # Plain text password - security warning
                display.warning(f"Plain text password detected for device {device_ip}. Using plain text credentials in configuration files is not secure.")
            else:
                new_device['password'] = password

        results['updated_inv_list'] = updated_inv_list
        return results

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

import copy
import os
from ansible.utils.display import Display
from ansible.plugins.action import ActionBase

display = Display()


class ActionModule(ActionBase):

    @staticmethod
    def _get_credentials_from_env(var_name):
        """
        Pull credentials from environment variables.
        If not found, return "not_set" strings.

        Note: Environment variables containing special characters like $, `, \\, etc.
        should be properly escaped when setting them in the shell.
        Example: export PASSWORD='MyP@$$w0rd' (use single quotes to prevent shell interpretation)
        """
        credential = os.getenv(var_name, 'not_set')

        # Check for potential shell interpretation issues
        if credential != 'not_set':
            # Check for common signs that shell interpretation may have occurred
            suspicious_patterns = ['$', '`', '\\']
            original_var = os.getenv(var_name)
            if original_var and any(char in var_name for char in suspicious_patterns):
                display.warning(f"Environment variable '{var_name}' contains special characters. "
                                f"Ensure it's properly quoted when setting: export {var_name}='your_value'"
                                f"Check documentation how to set your password")

        return credential

    def _get_switch_credentials_from_datamodel(self, data_model, management_ipv4_address):

        data_model_switches = data_model['vxlan']['topology']['switches']

        for switch in data_model_switches:
            if switch['management']['management_ipv4_address'] == management_ipv4_address:
                username = switch['management'].get('username', '')
                password = switch['management'].get('password', '')
                if username and password:
                    return username, password
                else:
                    return None

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['retrieve_failed'] = False

        data_model = self._task.args.get('data_model')

        key_username = 'ndfc_switch_username'
        key_password = 'ndfc_switch_password'
        key_discovery_username = 'ndfc_switch_discovery_username'
        key_discovery_password = 'ndfc_switch_discovery_password'

        ndfc_host_name = task_vars['inventory_hostname']
        username = task_vars['hostvars'][ndfc_host_name].get(key_username, '')
        password = task_vars['hostvars'][ndfc_host_name].get(key_password, '')
        discovery_username = task_vars['hostvars'][ndfc_host_name].get(key_discovery_username, '')
        discovery_password = task_vars['hostvars'][ndfc_host_name].get(key_discovery_password, '')

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

            # Try to get individual credentials from model data
            individual_credentials = self._get_switch_credentials_from_datamodel(data_model, device_ip)
            if individual_credentials:
                switch_username, switch_password = individual_credentials

                # Handle env_var_ prefix for switch-specific username
                if switch_username.startswith('env_var_'):
                    env_var_name = switch_username
                    switch_username = self._get_credentials_from_env(env_var_name)
                    if switch_username == 'not_set':
                        display.vv(f"Environment variable '{env_var_name}' not found for device {device_ip}. Using group_vars username.")
                        switch_username = username

                # Handle env_var_ prefix for switch-specific password
                if switch_password.startswith('env_var_'):
                    env_var_name = switch_password
                    switch_password = self._get_credentials_from_env(env_var_name)
                    if switch_password == 'not_set':
                        display.vv(f"Environment variable '{env_var_name}' not found for device {device_ip}. Using group_vars password.")
                        switch_password = password

                # Use individual credentials
                new_device['user_name'] = switch_username
                new_device['password'] = switch_password
                display.vvv(f"Using individual credentials from model data for device {device_ip}")
            else:
                # Use default group_vars credentials
                new_device['user_name'] = username
                new_device['password'] = password
                display.vvv(f"No individual credentials found in model data for device {device_ip}. Using group_vars credentials.")

            # Handle discovery credentials if applicable
            if 'poap' in new_device and new_device['poap']:
                discovery_user = new_device['poap'][0].get('discovery_username')
                discovery_pass = new_device['poap'][0].get('discovery_password')

                # Check for placeholder values indicating new credentials are needed for discovery
                is_placeholder = (
                    discovery_user == 'PLACE_HOLDER_USERNAME' or
                    discovery_pass == 'PLACE_HOLDER_PASSWORD'
                )
                if is_placeholder:
                    # Use group_vars discovery credentials
                    if discovery_username == '' or discovery_password == '':
                        display.warning(
                            f"No discovery credentials found for new user in group_vars for device {device_ip}. "
                            f"Skipping discovery credentials assignment and fallback to default behavior."
                        )
                        new_device['poap'][0].pop('discovery_username', None)
                        new_device['poap'][0].pop('discovery_password', None)
                    else:
                        new_device['poap'][0]['discovery_username'] = discovery_username
                        new_device['poap'][0]['discovery_password'] = discovery_password

        results['updated_inv_list'] = updated_inv_list
        return results

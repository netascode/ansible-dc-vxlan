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

# This is an example file for help functions that can be called by
# our various action plugins for common routines.
#
# For example in prepare_serice_model.py we can do the following:
#  from ..helper_functions import do_something


def data_model_key_check(tested_object, keys):
    """
    Check if key(s) are found and exist in the data model.

    :Parameters:
        :tested_object (dict): Data model to check for keys.
        :keys (list): List of keys to check in the data model.

    :Returns:
        :dm_key_dict (dict): Dictionary of lists for keys found, not found, and corresponding data or empty data.

    :Raises:
        N/A
    """
    dm_key_dict = {'keys_found': [], 'keys_not_found': [], 'keys_data': [], 'keys_no_data': []}
    for key in keys:
        if tested_object and key in tested_object:
            dm_key_dict['keys_found'].append(key)
            tested_object = tested_object[key]
            if tested_object:
                dm_key_dict['keys_data'].append(key)
            else:
                dm_key_dict['keys_no_data'].append(key)
        else:
            dm_key_dict['keys_not_found'].append(key)

    return dm_key_dict


def ndfc_get_switch_policy(self, task_vars, tmp, switch_serial_number):
    """
    Get NDFC policy for a given managed switch by the switch's serial number.

    :Parameters:
        :self: Ansible action plugin instance object.
        :task_vars (dict): Ansible task vars.
        :tmp (None, optional): Ansible tmp object. Defaults to None via Action Plugin.
        :switch_serial_number (str): The serial number of the managed switch for which the NDFC policy is to be retrieved.

    :Returns:
        :policy_data: The NDFC policy data for the given switch.

    :Raises:
        N/A
    """
    policy_data = self._execute_module(
        module_name="cisco.dcnm.dcnm_rest",
        module_args={
            "method": "GET",
            "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/policies/switches/{switch_serial_number}/SWITCH/SWITCH"
        },
        task_vars=task_vars,
        tmp=tmp
    )

    return policy_data


def ndfc_get_switch_policy_using_template(self, task_vars, tmp, switch_serial_number, template_name):
    """
    Get NDFC policy for a given managed switch by the switch's serial number and a specified NDFC template name.

    :Parameters:
        :self: Ansible action plugin instance object.
        :task_vars (dict): Ansible task vars.
        :tmp (None, optional): Ansible tmp object. Defaults to None via Action Plugin.
        :switch_serial_number (str): The serial number of the managed switch for which the NDFC policy is to be retrieved.
        :template_name (str): The name of the NDFC template for which the policy is to be retrieved.

    :Returns:
        :policy_match: The NDFC policy data for the given switch and matching template.

    :Raises:
        :Exception: If the policy for the given switch and template is not found.
    """
    policy_data = ndfc_get_switch_policy(self, task_vars, tmp, switch_serial_number)

    try:
        policy_match = next(
            (item for item in policy_data["response"]["DATA"] if item["templateName"] == template_name and item['serialNumber'] == switch_serial_number)
        )
    except StopIteration:
        err_msg = f"Policy for template {template_name} and switch {switch_serial_number} not found!"
        err_msg += f" Please ensure switch with serial number {switch_serial_number} is part of the fabric."
        raise Exception(err_msg)

    return policy_match


def ndfc_get_nac_switch_policy_using_desc(self, task_vars, tmp, switch_serial_number):
    """
    Get NDFC policy for a given managed switch by the switch's serial number and the prepanded string nac.

    :Parameters:
        :self: Ansible action plugin instance object.
        :task_vars (dict): Ansible task vars.
        :tmp (None, optional): Ansible tmp object. Defaults to None via Action Plugin.
        :switch_serial_number (str): The serial number of the managed switch for which the NDFC policy is to be retrieved.

    :Returns:
        :policy_match: The NDFC policy data for the given switch and matching template.

    :Raises:
        N/A
    """
    policy_data = ndfc_get_switch_policy(self, task_vars, tmp, switch_serial_number)

    policy_match = [
        item for item in policy_data["response"]["DATA"]
        if item.get("description", None) and "nac_" in item.get("description", None) and item["source"] == ""
    ]

    return policy_match

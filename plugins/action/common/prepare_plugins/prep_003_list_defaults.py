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

from ansible.utils.display import Display
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import data_model_key_check
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.data_model_keys import model_keys
from functools import reduce
import operator

display = Display()


def getFromDict(dataDict, mapList):
    """
    # Summary

    Get subset of a nested Dict from a list of keys

    """
    return reduce(operator.getitem, mapList, dataDict)


def update_nested_dict(nested_dict, keys, new_value):
    """
    # Summary

    Update nested dictionary element value

    ## Raises

    None

    ## Parameters

    -   nested_dict: Dictionary to be updated
    -   keys: A list of keys to access the value
    -   value: Update the key with this value

    ## Updates

    Updates nested_dict

    ## Usage

    ```python

    update_nested_dict(self.data_model, keys, [])

    ```
    """
    if len(keys) == 1:
        nested_dict[keys[0]] = new_value
    else:
        key = keys[0]
        if key in nested_dict:
            update_nested_dict(nested_dict[key], keys[1:], new_value)


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def set_list_default(self, parent_keys, target_key):
        """
        # Summary

        Defaults a target_key to be an empty list [] if the
        target_key does not exist or does exist but there is no
        data associated with the target_key.

        ## Raises

        None

        ## Parameters

        -   parent_keys: A list of parent keys
        -   target_key: The key under the parent keys to access the list

        ## Updates

        Updates self.data_model

        ## Usage

        ```python
        parent_keys = ['vxlan', 'global', 'dns_servers']
        target_key = 'dns_servers'

        self.set_list_default(parent_keys, target_key)

        ```
        """
        keys = parent_keys + [target_key]
        dm_check = data_model_key_check(self.data_model, keys)
        if target_key in dm_check['keys_not_found'] or \
           target_key in dm_check['keys_no_data']:
            update_nested_dict(self.data_model, keys, [])

    def set_nested_list_default(self, data_model_subset, target_key):
        """
        # Summary

        Update part of a data_model dictionary that has an arbitrary
        list of items that needs to be set to empty list []

        ## Raises

        None

        ## Parameters

        -   data_model_subset: Model data subset entry point
        -   target_key: The target key for each list item under the entry point

        ## Updates

        Updates self.data_model

        ## Usage

        ```python

        data_model_subset = self.data_model['vxlan']['topology']['switches']
        target_key = 'freeforms'

        self.set_nested_list_default(data_model_subset, target_key)

        ```
        """
        list_index = 0
        for item in data_model_subset:
            dm_check = data_model_key_check(item, [target_key])
            if target_key in dm_check['keys_not_found'] or target_key in dm_check['keys_no_data']:
                data_model_subset[list_index][target_key] = []

            list_index += 1

        # The code in this set_nested_list_default function effectively replaces this pattern:
        #
        # for switch in self.data_model['vxlan']['topology']['switches']:
        #     dm_check = data_model_key_check(switch, ['freeforms'])
        #     if 'freeforms' in dm_check['keys_not_found'] or \
        #     'freeforms' in dm_check['keys_no_data']:
        #         self.data_model['vxlan']['topology']['switches'][list_index]['freeforms'] = []

        #     list_index += 1

    # The prepare method is used to default each list or nested list
    # in the model data to an empty list if the key for the list does
    # not exist or data under they key does not exist.
    #
    # This is to ensure that the model data is consistent and can be
    # used by other plugins without having to check if the key exists.
    def prepare(self):
        self.data_model = self.kwargs['results']['model_extended']

        # --------------------------------------------------------------------
        # Fabric Global List Defaults
        # --------------------------------------------------------------------
        fabric_type = self.data_model['vxlan']['fabric']['type']

        # for path in paths:
        for path in model_keys[fabric_type]:
            # Get all but the last 2 elements of model_keys[path]
            path_type = model_keys[fabric_type][path][-1]
            parent_keys = model_keys[fabric_type][path][:-2]
            target_key = model_keys[fabric_type][path][-2]
            if path_type == 'KEY':
                dm_check = data_model_key_check(self.data_model, parent_keys + [target_key])
                if target_key in dm_check['keys_not_found'] or target_key in dm_check['keys_no_data']:
                    update_nested_dict(self.data_model, parent_keys + [target_key], {})
            if path_type == 'LIST':
                self.set_list_default(parent_keys, target_key)
            if path_type == 'LIST_INDEX':
                # model_keys['VXLAN_EVPN']['topology.switches.freeform'] = [root_key, 'topology', 'switches', 'freeform', 'LIST_INDEX']
                data_model_subset = getFromDict(self.data_model, parent_keys)
                self.set_nested_list_default(data_model_subset, target_key)

        # Quick Sanity Check:
        #
        # For Fabric Type: VXLAN_EVPN or External
        #  * Check for existence of global or underlay data
        #
        # There might actualy be data but one of the other model files might
        # have a bug or everything except the top level vxlan key is commented out.
        if fabric_type in ['VXLAN_EVPN', 'External', 'eBGP_VXLAN']:
            fn = self.data_model['vxlan']['fabric']['name']
            if not bool(self.data_model['vxlan'].get('underlay')):
                msg = "((vxlan.underlay)) data is empty! Check your host_vars model data for fabric {fn}."
                display.warning(msg=msg, formatted=True)
            if not bool(self.data_model['vxlan'].get('global')):
                msg = "((vxlan.global)) data is empty! Check your host_vars model data for fabric {fn}."
                display.warning(msg=msg, formatted=True)

        self.kwargs['results']['model_extended'] = self.data_model
        return self.kwargs['results']

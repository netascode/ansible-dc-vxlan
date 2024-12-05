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
from ....plugin_utils.helper_functions import data_model_key_check

display = Display()


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        model_data = self.kwargs['results']['model_extended']

        parent_keys = ['vxlan', 'fabric']
        dm_check = data_model_key_check(model_data, parent_keys)
        if 'fabric' in dm_check['keys_not_found'] or 'fabric' in dm_check['keys_no_data']:
            display.deprecated(
                "Attempting to use vxlan.global.name and vxlan.global.fabric_type due to vxlan.fabric.name and vxlan.fabric.type not being found. "
                "vxlan.global.name and vxlan.global.fabric_type is being deprecated. Please use vxlan.fabric."
            )

            # Prepare the data model to ensure vxlan.fabric.name is set
        #     global_data_check = False
        #     parent_keys = ['vxlan', 'global']
        #     dm_check = data_model_key_check(model_data, parent_keys)
        #     if 'global' in dm_check['keys_found'] and 'global' in dm_check['keys_data']:
        #         parent_keys = ['vxlan', 'global', 'name']
        #         dm_check = data_model_key_check(model_data, parent_keys)
        #         if 'name' in dm_check['keys_found'] and 'name' in dm_check['keys_data']:
        #             model_data['vxlan']['fabric']['name'] = model_data['vxlan']['global']['name']
        #         else:
        #             global_data_check = True

        #         parent_keys = ['vxlan', 'global', 'fabric_type']
        #         dm_check = data_model_key_check(model_data, parent_keys)
        #         if 'fabric_type' in dm_check['keys_found'] and 'fabric_type' in dm_check['keys_data']:
        #             model_data['vxlan']['fabric']['type'] = model_data['vxlan']['global']['fabric_type']
        #         else:
        #             self.kwargs['results']['failed'] = True
        #             self.kwargs['results']['msg'] = "vxlan.fabric is not set in the model data."
        #             global_data_check = True
        #     else:
        #         self.kwargs['results']['failed'] = True
        #         self.kwargs['results']['msg'] = "vxlan.fabric is not set in the model data."

        #     if global_data_check:
        #         self.kwargs['results']['failed'] = True
        #         self.kwargs['results']['msg'] = "vxlan.fabric is not set in the model data."
        # else:
        #     parent_keys = ['vxlan', 'fabric', 'name']
        #     dm_check = data_model_key_check(model_data, parent_keys)
        #     if 'name' in dm_check['keys_no_data'] or 'name' in dm_check['keys_not_found']:
        #         parent_keys = ['vxlan', 'global', 'name']
        #         dm_check = data_model_key_check(model_data, parent_keys)
        #         if 'name' in dm_check['keys_data']:
        #             # Insert warning about deprecation and where found
        #             model_data['vxlan']['fabric']['name'] = model_data['vxlan']['global']['name']
        #         else:
        #             self.kwargs['results']['failed'] = True
        #             self.kwargs['results']['msg'] = "vxlan.fabric.name is not set in the model data."

        #     # Prepare the data model to ensure vxlan.fabric.type is set
        #     parent_keys = ['vxlan', 'fabric', 'type']
        #     dm_check = data_model_key_check(model_data, parent_keys)
        #     if 'type' in dm_check['keys_no_data'] or 'name' in dm_check['keys_not_found']:
        #         parent_keys = ['vxlan', 'global', 'fabric_type']
        #         dm_check = data_model_key_check(model_data, parent_keys)
        #         if 'fabric_type' in dm_check['keys_data']:
        #             # Insert warning about deprecation and where found
        #             model_data['vxlan']['fabric']['type'] = model_data['vxlan']['global']['fabric_type']
        #         else:
        #             self.kwargs['results']['failed'] = True
        #             self.kwargs['results']['msg'] = "vxlan.fabric.type is not set in the model data."

        # 1 - no fabric key data model
        # 2a - fabric key data model with no data (i.e. no name or type) > semantic valdiation failure with schema
        # 2b - fabric key data model with no data (i.e. name or type) > check if we have global name and global fabric_type 


        # insert comment to indicate this is a oneoff check for fabric key as this should really be done in a rule, 
        # but fabric name and key are foundational for the collection so we need to ensure it is set.
        # this prepare plugin also helps retain backwards compatibility with the global fabric name and fabric_type keys previously used.

        # Prepare the data model to ensure vxlan.fabric.name is set

        self.kwargs['results']['model_extended'] = model_data
        return self.kwargs['results']

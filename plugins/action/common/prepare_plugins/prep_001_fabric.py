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

        # !!! WARNING !!!
        # ------------------------------------------------------------------------------------------
        # If you are debugging problems with the data model and sections are missing make sure
        # you don't have any data files with only the toplevel vxlan: key.  This can cause problems
        # where IaC validate removes sections of the model data, like the vxlan.underlay section
        # ------------------------------------------------------------------------------------------

        if not bool(model_data):
            msg = 'Model data is empty! It is possible there is no data in host_vars or there'
            msg += ' might be a bug in the model data.  Please check host_vars for this fabric.'
            msg += ' Possible reasons: duplicate keys, unsupported keys, invalid yaml etc...'
            self.kwargs['results']['failed'] = True
            self.kwargs['results']['msg'] = msg
            return self.kwargs['results']

        # Checking for fabric key in the data model.
        # This type of check should be done in a rule, but fabric.name and fabric.type are foundational for the collection so we need to ensure it is set.
        # This prepare plugin also helps retain backwards compatibility with global.name and global.fabric_type keys previously used.
        parent_keys = ['vxlan', 'fabric']
        dm_check = data_model_key_check(model_data, parent_keys)
        if 'fabric' in dm_check['keys_not_found'] or 'fabric' in dm_check['keys_no_data']:
            deprecated_msg = (
                "Attempting to use vxlan.global.name and vxlan.global.fabric_type due to "
                "vxlan.fabric.name and vxlan.fabric.type not being defined. "
                "vxlan.global.name and vxlan.global.fabric_type is being deprecated. Please use vxlan.fabric."
            )
            display.deprecated(msg=deprecated_msg, version="1.0.0")

            parent_keys = ['vxlan', 'global']
            dm_check = data_model_key_check(model_data, parent_keys)
            if 'global' in dm_check['keys_found'] and 'global' in dm_check['keys_data']:
                model_data['vxlan'].update({'fabric': {}})
                parent_keys = ['vxlan', 'global', 'name']
                dm_check = data_model_key_check(model_data, parent_keys)
                if 'name' in dm_check['keys_found'] and 'name' in dm_check['keys_data']:
                    model_data['vxlan']['fabric'].update({'name': model_data['vxlan']['global']['name']})
                else:
                    self.kwargs['results']['failed'] = True
                    self.kwargs['results']['msg'] = "vxlan.global.name is not defined in the data model. Please set vxlan.fabric.name."

                parent_keys = ['vxlan', 'global', 'fabric_type']
                dm_check = data_model_key_check(model_data, parent_keys)
                if 'fabric_type' in dm_check['keys_found'] and 'fabric_type' in dm_check['keys_data']:
                    model_data['vxlan']['fabric'].update({'type': model_data['vxlan']['global']['fabric_type']})
                else:
                    self.kwargs['results']['failed'] = True
                    self.kwargs['results']['msg'] = "vxlan.global.fabric_type is not defined in the data model. Please set vxlan.fabric.type."
            else:
                self.kwargs['results']['failed'] = True
                self.kwargs['results']['msg'] = "vxlan.fabric is not set in the model data."

        else:
            # Prepare the data model to ensure vxlan.fabric.name is set
            parent_keys = ['vxlan', 'fabric', 'name']
            dm_check = data_model_key_check(model_data, parent_keys)
            if 'name' in dm_check['keys_no_data'] or 'name' in dm_check['keys_not_found']:
                deprecated_msg = (
                    "Attempting to use vxlan.global.name due to vxlan.fabric.name not being defined. "
                    "vxlan.global.name is being deprecated. Please use vxlan.fabric."
                )
                display.deprecated(msg=deprecated_msg, version="1.0.0")
                parent_keys = ['vxlan', 'global', 'name']
                dm_check = data_model_key_check(model_data, parent_keys)
                if 'name' in dm_check['keys_data']:
                    model_data['vxlan']['fabric'].update({'name': model_data['vxlan']['global']['name']})
                else:
                    self.kwargs['results']['failed'] = True
                    self.kwargs['results']['msg'] = "vxlan.fabric.name is not defined in the data model."

            # Prepare the data model to ensure vxlan.fabric.type is set
            parent_keys = ['vxlan', 'fabric', 'type']
            dm_check = data_model_key_check(model_data, parent_keys)
            if 'type' in dm_check['keys_no_data'] or 'type' in dm_check['keys_not_found']:
                deprecated_msg = (
                    "Attempting to use vxlan.global.type due to vxlan.fabric.type not being defined. "
                    "vxlan.global.type is being deprecated. Please use vxlan.fabric."
                )
                display.deprecated(msg=deprecated_msg, version="1.0.0")
                parent_keys = ['vxlan', 'global', 'fabric_type']
                dm_check = data_model_key_check(model_data, parent_keys)
                if 'fabric_type' in dm_check['keys_data']:
                    model_data['vxlan']['fabric'].update({'type': model_data['vxlan']['global']['fabric_type']})
                else:
                    self.kwargs['results']['failed'] = True
                    self.kwargs['results']['msg'] = "vxlan.fabric.type is not defined in the data model."


        # For backwards compatibility, replace 'overlay_services' key with 'overlay'
        # NOTE: No prepare plugin, jinja2 template or ansible task should reference 'overlay_services' after this replacement.
        # NOTE: Rules are different since rules run BEFORE prepare plugins
        # import epdb ; epdb.set_trace()
        parent_keys = ['vxlan', 'overlay_services']
        dm_check = data_model_key_check(model_data, parent_keys)
        if 'overlay_services' in dm_check['keys_found']:
            deprecated_msg = (
                "vxlan.overlay_services is being deprecated. "
                "Please use vxlan.overlay instead"
            )
            display.deprecated(msg=deprecated_msg, version="1.0.0")
            model_data['vxlan']['overlay'] = model_data['vxlan']['overlay_services']
            del model_data['vxlan']['overlay_services']

        parent_keys = ['vxlan', 'multisite', 'overlay']
        dm_check = data_model_key_check(model_data, parent_keys)
        if 'multisite' in dm_check['keys_found'] and 'overlay' in dm_check['keys_found']:
            model_data['vxlan']['overlay'] = model_data['vxlan']['multisite']['overlay']


        self.kwargs['results']['model_extended'] = model_data
        return self.kwargs['results']

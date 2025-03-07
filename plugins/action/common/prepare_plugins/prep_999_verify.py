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
from ....plugin_utils.data_model_keys import model_keys

display = Display()


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        model_data = self.kwargs['results']['model_extended']
        self.kwargs['results']['failed'] = False
        self.kwargs['results']['msg'] = None
        fail_msg = "Mandatory key ({}) not found in prepared data model!"
        fail_msg += " There is either a bug in one of the prepare plugins or"
        fail_msg += " the data was not included in the data model."
        fail_msg += " Data Model Section: ({})"

        # This prepare plugin serves as a final sanity check after all of the
        # previous prepare plugins have been called to transform the model data.
        #
        # This plugin ensures the following:
        #   * All keys required for this collection to function are present (not accidentally overwritten)
        #   * List items that were present before the prepare plugins ran are still present
        fabric_type = model_data['vxlan']['fabric']['type']
        for key in model_keys[fabric_type].keys():
            # Remove the meta_data item from model_keys entry (KEY, LIST, LIST_INDEX)
            model_keys[fabric_type][key].pop()
            dm_check = data_model_key_check(model_data, model_keys[fabric_type][key])
            # Example:
            # model_keys['VXLAN_EVPN']['policy.policies'] = [root_key, 'policy', 'policies', 'LIST']
            #   * Get 2nd to last item from the python list above
            #   * model_keys[key][-2] - Gets 'policies'
            if model_keys[fabric_type][key][-2] in dm_check['keys_not_found']:
                self.kwargs['results']['failed'] = True
                self.kwargs['results']['msg'] = fail_msg.format(key, model_keys[fabric_type][key])
                return self.kwargs['results']

        # We don't need to pass any data back in this plugin because we don't modify any data.
        return self.kwargs['results']

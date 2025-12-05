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

import hashlib
import os
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import hostname_to_ip_mapping, data_model_key_check


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        data_model = self.kwargs['results']['model_extended']

        # Loop through policies and extract 'filename' when present and calculate md5
        policies = data_model['vxlan'].get('policy', [])
        if policies:
            for policy in policies['policies']:
                filename = policy.get('filename')

                if filename:
                    abs_path = os.path.expanduser(filename)

                    with open(abs_path, 'r', encoding='utf-8') as file:
                        data = file.read()

                    md5 = hashlib.md5(data.encode()).hexdigest()
                    policy.update({'md5': md5})

        self.kwargs['results']['model_extended'] = data_model

        return self.kwargs['results']

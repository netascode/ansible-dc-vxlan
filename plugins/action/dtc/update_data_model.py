# Copyright (c) 2025 Cisco Systems, Inc. and its affiliates
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function


__metaclass__ = type

import re
import os
import hashlib

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase


display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)

        data_model = self._task.args['data_model']
        policies = data_model['vxlan'].get('policy', [])

        # Loop through policies and extract 'filename' when present
        for policy in policies['policies']:
            filename = policy.get('filename')

            if filename:
                # Normalize tilde (~) and environment variables if present
                abs_path = os.path.expanduser(filename)

                with open(abs_path, 'r', encoding='utf-8') as file:
                    data = file.read()

                # import epdb; epdb.serve(port=5555)
                # Define a pattern to normalize old and new data
                pattern = r'__omit_place_holder__\S+'
                data = re.sub(pattern, 'NORMALIZED', data, flags=re.MULTILINE)
                md5 = hashlib.md5(data.encode()).hexdigest()
                policy.update({'md5': md5})

        results['data'] = data_model
        return results

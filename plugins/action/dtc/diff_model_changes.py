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
import hashlib
import re
import os

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        # self._supports_async = True
        results = super(ActionModule, self).run(tmp, task_vars)
        results['file_data_changed'] = False

        file_name_previous = self._task.args['file_name_previous']
        file_name_current = self._task.args['file_name_current']

        # Check if the previous file exists and if not return results
        # indicating that the file data has changed
        if not os.path.exists(file_name_previous):
            results['file_data_changed'] = True
            return results

        # Read the contents of the previous and current files
        with open(file_name_previous, 'r') as file:
            data_previous = file.read()

        with open(file_name_current, 'r') as file:
            data_current = file.read()

        # Compare the MD5 hash of the previous and current files
        md5_previous = hashlib.md5(data_previous.encode()).hexdigest()
        md5_current = hashlib.md5(data_current.encode()).hexdigest()
        if md5_previous == md5_current:
            # Delete previous data file and if the MD5 hashes are the same
            os.remove(file_name_previous)
            return results

        # If we get here then file contents did not match but it may be due to
        # the _omit_place_holder_ values that are used in the data model

        # Define a pattern to normalize old and new data
        pattern = r'__omit_place_holder__\S+'

        # Replace lines that match the pattern with a new line
        data_previous = re.sub(pattern, 'NORMALIZED', data_previous, flags=re.MULTILINE)
        md5_previous = hashlib.md5(data_previous.encode()).hexdigest()

        # Replace lines that match the pattern with a new line
        data_current = re.sub(pattern, 'NORMALIZED', data_current, flags=re.MULTILINE)
        md5_current = hashlib.md5(data_current.encode()).hexdigest()

        # Compare the MD5 hash of the normalized previous and current files
        if md5_previous == md5_current:
            # Delete previous data file and if the MD5 hashes are the same
            os.remove(file_name_previous)
            return results

        # If we get here then file contents did not match even after normalizing
        results['file_data_changed'] = True

        return results

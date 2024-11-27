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
from ansible.errors import AnsibleError

try:
    from iac_validate.yaml import load_yaml_files
    from iac_validate.cli.options import DEFAULT_SCHEMA
except ImportError as imp_exc:
    IAC_VALIDATE_IMPORT_ERROR = imp_exc
else:
    IAC_VALIDATE_IMPORT_ERROR = None

import os

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False
        results['msg'] = None
        results['data'] = {}

        if IAC_VALIDATE_IMPORT_ERROR:
            raise AnsibleError('iac-validate not found and must be installed. Please pip install iac-validate.') from IAC_VALIDATE_IMPORT_ERROR

        mdata = self._task.args.get('mdata')

        # Verify That Data Sources Exists
        if mdata and not os.path.exists(mdata):
            results['failed'] = True
            results['msg'] = "The data directory ({0}) for this fabric does not appear to exist!".format(mdata)
            return results
        if len(os.listdir(mdata)) == 0:
            results['failed'] = True
            results['msg'] = "The data directory ({0}) for this fabric is empty!".format(mdata)
            return results

        # Return Schema Validated Model Data
        results['data'] = load_yaml_files([mdata])

        return results

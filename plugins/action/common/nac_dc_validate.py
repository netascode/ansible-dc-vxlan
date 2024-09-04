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

import iac_validate.validator
from iac_validate.yaml import load_yaml_files
from iac_validate.cli.options import DEFAULT_SCHEMA
import os

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False
        results['msg'] = None
        results['data'] = {}

        schema = self._task.args.get('schema')
        rules = self._task.args.get('rules')
        mdata = self._task.args.get('mdata')

        # Generate a warning if the Schema and Rules are not provided
        if 'schema' in locals() and (schema == "" or not os.path.exists(schema)):
            display.warning("The schema ({0}) does not appear to exist! ".format(schema))
        if 'rules' in locals() and (rules == "" or not os.path.exists(rules)):
            display.warning("The rules directory ({0}) does not appear to exist! ".format(rules))
        # The rules directory is considered empty if it is an empty dir or only contains the .gitkeep file
        if os.path.exists(rules) and (not os.listdir(rules) or (len(os.listdir(rules)) == 1 and '.gitkeep' in os.listdir(rules))):
            display.warning("The rules directory ({0}) exists but is empty! ".format(rules))

        # Verify That Data Sources Exists
        if mdata and not os.path.exists(mdata):
            results['failed'] = True
            results['msg'] = "The data directory ({0}) for this fabric does not appear to exist!".format(mdata)
            return results
        if len(os.listdir(mdata)) == 0:
            results['failed'] = True
            results['msg'] = "The data directory ({0}) for this fabric is empty!".format(mdata)
            return results

        if schema == '':
            schema = DEFAULT_SCHEMA

        validator = iac_validate.validator.Validator(schema, rules)
        if schema:
            validator.validate_syntax([mdata])
        if rules:
            validator.validate_semantics([mdata])

        msg = ""
        for error in validator.errors:
            msg += error + "\n"

        if msg:
            results['failed'] = True
            results['msg'] = msg

        # Return Schema Validated Model Data
        results['data'] = load_yaml_files([mdata])

        return results

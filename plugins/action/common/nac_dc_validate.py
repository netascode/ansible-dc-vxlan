from __future__ import absolute_import, division, print_function


__metaclass__ = type

from ansible import constants as C
from ansible.utils.display import Display
from ansible.plugins.action import ActionBase

from ..helper_functions import do_something

import iac_validate.validator
from iac_validate.yaml import load_yaml_files
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
        if schema and not os.path.exists(schema):
            display.warning("The schema ({0}) does not appear to exist! ".format(schema))
        if not os.path.exists(rules):
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

        if schema is None:
            schema = ""
        if rules is None:
            rules = ""

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
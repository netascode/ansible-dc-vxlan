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

from __future__ import absolute_import, division, print_function


__metaclass__ = type

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleError

try:
    from nac_yaml.yaml import load_yaml_files
except ImportError as imp_yaml_exc:
    NAC_YAML_IMPORT_ERROR = imp_yaml_exc
else:
    NAC_YAML_IMPORT_ERROR = None


def _load_model_files(paths):
    # nac-yaml >= 2.0.0 accepts typ='safe' (C-accelerated safe loader; ~5x faster
    # model load on large fabrics when ruamel.yaml.clib is present). nac-yaml < 2.0.0
    # has no typ kwarg, so fall back to the default loader to stay backward-compatible.
    try:
        return load_yaml_files(paths, typ='safe')
    except TypeError:
        return load_yaml_files(paths)


try:
    import nac_validate.validator
    import yamale
    from yamale import YamaleError
    try:
        # nac-validate >= 2.0.0
        from nac_validate.constants import DEFAULT_SCHEMA
    except ImportError:
        # nac-validate < 2.0.0
        from nac_validate.cli.defaults import DEFAULT_SCHEMA
except ImportError as imp_val_exc:
    NAC_VALIDATE_IMPORT_ERROR = imp_val_exc
else:
    NAC_VALIDATE_IMPORT_ERROR = None

try:
    # nac-validate >= 2.0.0 raises ValidationError subclasses (each carrying .errors)
    # from validate_syntax()/validate_semantics() instead of populating validator.errors
    from nac_validate.exceptions import ValidationError as _NacValidationError
except ImportError:
    class _NacValidationError(Exception):
        pass

import os
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import data_model_key_check

display = Display()

_ValidatorBase = nac_validate.validator.Validator if NAC_VALIDATE_IMPORT_ERROR is None else object


class OptimizedValidator(_ValidatorBase):

    def validate_syntax(self, input_paths, strict=True):
        # When the merged data model is already loaded (self.data), validate the
        # schema once against it instead of reloading and schema-checking every
        # input file. The stock per-file path re-parses all YAML and dominates
        # validate runtime on large fabrics (~8s -> sub-second here).
        if self.data is not None and self.schema is not None:
            try:
                yamale.validate(self.schema, [(self.data, str(input_paths[0]))], strict=strict)
            except YamaleError as syntax_exc:
                for result in syntax_exc.results:
                    for error in result.errors:
                        self.errors.append(f"Syntax error '{result.data}': {error}")
            return bool(self.errors)
        return super().validate_syntax(input_paths, strict)


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False
        results['msg'] = None

        if NAC_YAML_IMPORT_ERROR:
            raise AnsibleError('nac-yaml not found and must be installed. Please pip install nac-yaml.') from NAC_YAML_IMPORT_ERROR

        if NAC_VALIDATE_IMPORT_ERROR:
            raise AnsibleError('nac-validate not found and must be installed. Please pip install nac-validate.') from NAC_VALIDATE_IMPORT_ERROR

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

        rules_list = []
        data_model_loaded = None
        if rules and task_vars['role_path'] in rules:
            # Load in-memory data model using iac-validate
            # Perform the load in this if block to avoid loading the data model multiple times when custom enhanced rules are provided
            results['data'] = _load_model_files([mdata])
            data_model_loaded = results['data']

            # Introduce common directory to the rules list by default once vrf and network rules are updated
            parent_keys = ['vxlan', 'fabric']
            check = data_model_key_check(results['data'], parent_keys)
            if 'fabric' in check['keys_found'] and 'fabric' in check['keys_data']:
                if 'type' in results['data']['vxlan']['fabric']:
                    if results['data']['vxlan']['fabric']['type'] in ('VXLAN_EVPN'):
                        rules_list.append(f'{rules}common')
                        rules_list.append(f'{rules}ibgp_vxlan/')
                        rules_list.append(f'{rules}common_vxlan')
                    elif results['data']['vxlan']['fabric']['type'] in ('eBGP_VXLAN'):
                        rules_list.append(f'{rules}common')
                        rules_list.append(f'{rules}ebgp_vxlan/')
                        rules_list.append(f'{rules}common_vxlan')
                    elif results['data']['vxlan']['fabric']['type'] in ('MSD', 'MCFG'):
                        rules_list.append(f'{rules}multisite/')
                    elif results['data']['vxlan']['fabric']['type'] in ('ISN'):
                        rules_list.append(f'{rules}isn/')
                    elif results['data']['vxlan']['fabric']['type'] in ('External'):
                        rules_list.append(f'{rules}common')
                        rules_list.append(f'{rules}external/')
                    else:
                        results['failed'] = True
                        results['msg'] = f"vxlan.fabric.type {results['data']['vxlan']['fabric']['type']} is not a supported fabric type."
                else:
                    results['failed'] = True
                    results['msg'] = "vxlan.fabric.type is not defined in the data model."
            else:
                # This else block is to be removed after the deprecation of vxlan.global.fabric_type
                parent_keys = ['vxlan', 'global']
                check = data_model_key_check(results['data'], parent_keys)
                if 'global' in check['keys_found'] and 'global' in check['keys_data']:
                    if 'fabric_type' in results['data']['vxlan']['global']:
                        deprecated_msg = (
                            "Attempting to use vxlan.global.fabric_type due to vxlan.fabric.type not being found. "
                            "vxlan.global.fabric_type is being deprecated. Please use vxlan.fabric.type."
                        )
                        display.deprecated(msg=deprecated_msg, version='1.0.0', collection_name='cisco.nac_dc_vxlan')

                        if results['data']['vxlan']['global']['fabric_type'] in ('VXLAN_EVPN'):
                            rules_list.append(f'{rules}common')
                            rules_list.append(f'{rules}ibgp_vxlan/')
                            rules_list.append(f'{rules}common_vxlan')
                        elif results['data']['vxlan']['global']['fabric_type'] in ('MSD', 'MCFG'):
                            rules_list.append(f'{rules}multisite/')
                        elif results['data']['vxlan']['global']['fabric_type'] in ('ISN'):
                            rules_list.append(f'{rules}isn/')
                        elif results['data']['vxlan']['global']['fabric_type'] in ('External'):
                            rules_list.append(f'{rules}common')
                            rules_list.append(f'{rules}external/')
                        elif results['data']['vxlan']['global']['fabric_type'] in ('eBGP_VXLAN'):
                            results['failed'] = True
                            results['msg'] = f"Fabric type {results['data']['vxlan']['global']['fabric_type']} requires using vxlan.fabric.type."
                        else:
                            results['failed'] = True
                            results['msg'] = f"vxlan.fabric.type {results['data']['vxlan']['global']['fabric_type']} is not a supported fabric type."
                    else:
                        results['failed'] = True
                        results['msg'] = "vxlan.fabric.type is not defined in the data model."
        else:
            # Else block to pickup custom enhanced rules provided by the user
            rules_list.append(f'{rules}')

        # Ensure the merged data model is loaded before validation so the schema
        # (syntax) check runs once against it rather than reloading every file.
        if rules_list and data_model_loaded is None:
            data_model_loaded = _load_model_files([mdata])
            results['data'] = data_model_loaded

        if rules_list and schema:
            syntax_validator = OptimizedValidator(schema, rules_list[0])
            if syntax_validator.schema is not None:
                syntax_validator.data = data_model_loaded
                try:
                    syntax_validator.validate_syntax([mdata])
                    syntax_errors = list(syntax_validator.errors)
                except _NacValidationError as validation_exc:
                    syntax_errors = list(getattr(validation_exc, 'errors', None) or [str(validation_exc)])

                if syntax_errors:
                    results['failed'] = True
                    results['msg'] = "".join(error + "\n" for error in syntax_errors)
                    return results

        for rules_item in rules_list:
            if not rules_item:
                continue
            validator = OptimizedValidator(schema, rules_item)
            validator.data = data_model_loaded
            try:
                validator.validate_semantics([mdata])
                iteration_errors = list(validator.errors)
            except _NacValidationError as validation_exc:
                iteration_errors = list(getattr(validation_exc, 'errors', None) or [str(validation_exc)])

            msg = ""
            for error in iteration_errors:
                msg += error + "\n"

            if msg:
                results['failed'] = True
                results['msg'] = msg
                break

        return results

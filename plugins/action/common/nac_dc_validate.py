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

import difflib
import glob
import hashlib
import json
import logging
import os
import shutil

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleError

try:
    from nac_yaml.yaml import load_yaml_files
except ImportError as imp_yaml_exc:
    NAC_YAML_IMPORT_ERROR = imp_yaml_exc
else:
    NAC_YAML_IMPORT_ERROR = None

try:
    from nac_validate.validator import Validator
    from nac_validate.cli.defaults import DEFAULT_SCHEMA
    import yamale
    from yamale.yamale_error import YamaleError
except ImportError as imp_val_exc:
    NAC_VALIDATE_IMPORT_ERROR = imp_val_exc
    Validator = object
else:
    NAC_VALIDATE_IMPORT_ERROR = None

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import (
    data_model_key_check,
)

display = Display()
logger = logging.getLogger(__name__)


class OptimizedValidator(Validator):
    """Subclass of nac_validate.Validator that optimizes validate_syntax.

    When self.data is pre-populated with the merged data model, schema validation
    is performed once against the full model instead of per-file. This avoids
    redundant YAML loading and per-file schema checks (~5x speedup for large fabrics).
    """

    def validate_syntax(self, input_paths: list, strict: bool = True) -> bool:
        if self.data is not None and self.schema is not None:
            # Data already loaded - validate schema once against merged model
            try:
                yamale.validate(
                    self.schema, [(self.data, str(input_paths[0]))], strict=strict
                )
            except YamaleError as e:
                for result in e.results:
                    for err in result.errors:
                        msg = f"Syntax error '{result.data}': {err}"
                        logger.error(msg)
                        self.errors.append(msg)
        else:
            # Fall back to original per-file behavior
            return super().validate_syntax(input_paths, strict)
        if self.errors:
            return True
        return False


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False
        results['msg'] = None

        if NAC_YAML_IMPORT_ERROR:
            raise AnsibleError(
                'nac-yaml not found and must be installed. Please pip install nac-yaml.'
            ) from NAC_YAML_IMPORT_ERROR

        if NAC_VALIDATE_IMPORT_ERROR:
            raise AnsibleError(
                'nac-validate not found and must be installed. Please pip install nac-validate.'
            ) from NAC_VALIDATE_IMPORT_ERROR

        role_path = task_vars.get('role_path', '')
        playbook_dir = task_vars.get('playbook_dir', '')
        inventory_hostname = task_vars.get('inventory_hostname', '')
        inventory_dir = task_vars.get('inventory_dir', '')
        ansible_network_os = (
            task_vars.get('hostvars', {})
            .get(inventory_hostname, {})
            .get('ansible_network_os', '')
        )

        display.display(
            '----------------------------------------------------------------',
            color='cyan',
        )
        display.display(
            '+     Role - [cisco.nac_dc_vxlan.validate]                    +',
            color='cyan',
        )
        display.display(
            '----------------------------------------------------------------',
            color='cyan',
        )
        display.display(f'Role Path: {role_path}')
        display.display(f'Inventory Directory: {inventory_dir}')

        if ansible_network_os == 'cisco.nxos.nxos':
            display.display('Workflow: Direct to Device (DTD)', color='blue')
        elif ansible_network_os == 'cisco.dcnm.dcnm':
            display.display('Workflow: Direct to Controller (DTC)', color='blue')

        display.display('Validating and Preparing Service Model', color='cyan')

        schema = self._task.args.get('schema', '')
        rules = self._task.args.get('rules', '')
        mdata = self._task.args.get('mdata', '')
        enhanced_rules = self._task.args.get('enhanced_rules', '')

        if not mdata:
            mdata = os.path.join(playbook_dir, 'host_vars', inventory_hostname)
        if not rules:
            rules = os.path.join(role_path, 'files', 'rules') + '/'
        if not schema:
            schema = DEFAULT_SCHEMA

        if schema and schema != DEFAULT_SCHEMA and not os.path.exists(schema):
            display.warning(f'The schema ({schema}) does not appear to exist!')
        if rules and not os.path.exists(rules):
            display.warning(f'The rules directory ({rules}) does not appear to exist!')
        elif os.path.exists(rules) and (
            not os.listdir(rules)
            or (len(os.listdir(rules)) == 1 and '.gitkeep' in os.listdir(rules))
        ):
            display.warning(f'The rules directory ({rules}) exists but is empty!')

        if not os.path.exists(mdata):
            results['failed'] = True
            results['msg'] = (
                f'The data directory ({mdata}) for this fabric does not appear to exist!'
            )
            return results
        if len(os.listdir(mdata)) == 0:
            results['failed'] = True
            results['msg'] = f'The data directory ({mdata}) for this fabric is empty!'
            return results

        rules_list = []
        data_model_loaded = None
        if rules and task_vars['role_path'] in rules:
            # Load in-memory data model
            results['data'] = load_yaml_files([mdata])
            data_model_loaded = results['data']

            # Determine rules directories based on fabric type
            parent_keys = ['vxlan', 'fabric']
            check = data_model_key_check(results['data'], parent_keys)
            if 'fabric' in check['keys_found'] and 'fabric' in check['keys_data']:
                if 'type' in results['data']['vxlan']['fabric']:
                    fabric_type = results['data']['vxlan']['fabric']['type']
                    if fabric_type in ('VXLAN_EVPN',):
                        rules_list.append(f'{rules}common')
                        rules_list.append(f'{rules}ibgp_vxlan/')
                        rules_list.append(f'{rules}common_vxlan')
                    elif fabric_type in ('eBGP_VXLAN',):
                        rules_list.append(f'{rules}common')
                        rules_list.append(f'{rules}ebgp_vxlan/')
                        rules_list.append(f'{rules}common_vxlan')
                    elif fabric_type in ('MSD', 'MCFG'):
                        rules_list.append(f'{rules}multisite/')
                    elif fabric_type in ('ISN',):
                        rules_list.append(f'{rules}isn/')
                    elif fabric_type in ('External',):
                        rules_list.append(f'{rules}common')
                        rules_list.append(f'{rules}external/')
                    else:
                        results['failed'] = True
                        results['msg'] = (
                            f'vxlan.fabric.type {fabric_type} is not a supported fabric type.'
                        )
                else:
                    results['failed'] = True
                    results['msg'] = (
                        'vxlan.fabric.type is not defined in the data model.'
                    )
            else:
                # Deprecated fallback to vxlan.global.fabric_type
                parent_keys = ['vxlan', 'global']
                check = data_model_key_check(results['data'], parent_keys)
                if 'global' in check['keys_found'] and 'global' in check['keys_data']:
                    if 'fabric_type' in results['data']['vxlan']['global']:
                        deprecated_msg = (
                            'Attempting to use vxlan.global.fabric_type due to vxlan.fabric.type not being found. '
                            'vxlan.global.fabric_type is being deprecated. Please use vxlan.fabric.type.'
                        )
                        display.deprecated(
                            msg=deprecated_msg,
                            version='1.0.0',
                            collection_name='cisco.nac_dc_vxlan',
                        )

                        fabric_type = results['data']['vxlan']['global']['fabric_type']
                        if fabric_type in ('VXLAN_EVPN',):
                            rules_list.append(f'{rules}common')
                            rules_list.append(f'{rules}ibgp_vxlan/')
                            rules_list.append(f'{rules}common_vxlan')
                        elif fabric_type in ('MSD', 'MCFG'):
                            rules_list.append(f'{rules}multisite/')
                        elif fabric_type in ('ISN',):
                            rules_list.append(f'{rules}isn/')
                        elif fabric_type in ('External',):
                            rules_list.append(f'{rules}common')
                            rules_list.append(f'{rules}external/')
                        elif fabric_type in ('eBGP_VXLAN',):
                            results['failed'] = True
                            results['msg'] = (
                                f'Fabric type {fabric_type} requires using vxlan.fabric.type.'
                            )
                        else:
                            results['failed'] = True
                            results['msg'] = (
                                f'vxlan.fabric.type {fabric_type} is not a supported fabric type.'
                            )
                    else:
                        results['failed'] = True
                        results['msg'] = (
                            'vxlan.fabric.type is not defined in the data model.'
                        )
        else:
            # Custom enhanced rules provided by user
            rules_list.append(f'{rules}')

        # Append enhanced rules if provided
        if enhanced_rules and os.path.exists(enhanced_rules):
            rules_list.append(enhanced_rules)
            display.display(
                f'Enhanced rules detected and loaded: {enhanced_rules}', color='green'
            )
        elif enhanced_rules:
            display.warning(
                f'Enhanced rules path ({enhanced_rules}) does not exist, skipping.'
            )

        # Perform validation using OptimizedValidator (subclass override)
        # Schema validation done once with pre-loaded data
        if rules_list:
            first_validator = OptimizedValidator(schema, rules_list[0])
            if data_model_loaded is not None:
                first_validator.data = data_model_loaded
            if schema and first_validator.schema is not None:
                first_validator.validate_syntax([mdata])

            msg = ''
            for error in first_validator.errors:
                msg += error + '\n'
            if msg:
                results['failed'] = True
                results['msg'] = msg
                return results

            # Reuse loaded data for semantic validation across all rule sets
            if data_model_loaded is None:
                data_model_loaded = load_yaml_files([mdata])
                results['data'] = data_model_loaded

            for rules_item in rules_list:
                if rules_item:
                    validator = OptimizedValidator(schema, rules_item)
                    validator.data = data_model_loaded
                    validator.validate_semantics([mdata])

                    msg = ''
                    for error in validator.errors:
                        msg += error + '\n'
                    if msg:
                        results['failed'] = True
                        results['msg'] = msg
                        return results

        # Load and merge factory defaults with custom defaults from data model
        defaults_path = os.path.join(role_path, 'files', 'defaults.yml')
        factory_defaults = {}
        if os.path.isfile(defaults_path):
            from ruamel.yaml import YAML

            yaml_loader = YAML()
            with open(defaults_path) as f:
                defaults_content = yaml_loader.load(f)
            if defaults_content and 'factory_defaults' in defaults_content:
                factory_defaults = defaults_content['factory_defaults']

        custom_defaults = {}
        if data_model_loaded and isinstance(data_model_loaded, dict):
            custom_defaults = data_model_loaded.get('defaults') or {}

        results['defaults'] = _merge_dicts(
            dict(factory_defaults), dict(custom_defaults)
        )

        # Prepare service model (golden + extended)
        results = _prepare_service_model(
            results,
            data_model_loaded,
            results['defaults'],
            inventory_hostname,
            task_vars.get('hostvars', {}),
            os.path.join(role_path, '..', 'dtc', 'common', 'templates') + '/',
        )

        if results.get('failed'):
            return results

        # --- check_roles ---
        results['save_previous'] = False
        role_names = task_vars.get('ansible_play_role_names', [])
        for role in [
            'cisco.nac_dc_vxlan.create',
            'cisco.nac_dc_vxlan.deploy',
            'cisco.nac_dc_vxlan.remove',
        ]:
            if role in role_names:
                results['save_previous'] = True
                break

        # --- read_run_map ---
        import re
        import yaml
        from datetime import datetime as dt

        fabric_name = data_model_loaded['vxlan']['fabric']['name']
        play_tags = task_vars.get('ansible_run_tags', [])
        force_run_all = task_vars.get('force_run_all', False)
        display_model_diff_var = task_vars.get('display_model_diff', False)

        if 'dtc' in role_path:
            common_role_path = os.path.dirname(role_path)
            run_map_files_path = os.path.dirname(common_role_path) + '/validate/files'
        else:
            run_map_files_path = os.path.dirname(role_path) + '/validate/files'

        run_map_file_path = run_map_files_path + f'/{fabric_name}_run_map.yml'

        results['diff_run'] = True
        results['validate_only_run'] = False

        if not os.path.exists(run_map_file_path):
            results['diff_run'] = False
        else:
            with open(run_map_file_path, 'r') as file:
                previous_run_map = yaml.safe_load(file)

            for role in [
                'role_validate_completed',
                'role_create_completed',
                'role_deploy_completed',
                'role_remove_completed',
            ]:
                if not previous_run_map.get(role):
                    results['diff_run'] = False
                    break

            if play_tags and 'all' not in play_tags:
                results['diff_run'] = False

            if force_run_all is True:
                results['diff_run'] = False

            if len(play_tags) == 1 and 'role_validate' in play_tags:
                results['validate_only_run'] = True

        if not results['diff_run']:
            display.warning(
                f'Diff Run Feature is Disabled on this run for Fabric {fabric_name} '
                f"as one or more run map flags are `false` or `ansible_run_tags` is not 'all'."
            )

        # --- runtime mode ---
        results['validate_checksum_compare_enabled'] = (
            results['save_previous'] and results['diff_run'] and not bool(force_run_all)
        )
        results['validate_model_diff_enabled'] = results[
            'validate_checksum_compare_enabled'
        ] and bool(display_model_diff_var)

        # --- display runtime mode ---
        display.display(
            f'force_run_all={bool(force_run_all)}, '
            f"diff_run={results['diff_run']}, "
            f'ansible_run_tags={play_tags}, '
            f"checksum_compare={results['validate_checksum_compare_enabled']}, "
            f"display_model_diff={results['validate_model_diff_enabled']}",
            color='cyan',
        )

        # --- run_map starting_execution ---
        if not os.path.exists(run_map_files_path):
            os.makedirs(run_map_files_path, exist_ok=True)

        updated_run_map = {}
        updated_run_map['time_stamp'] = re.sub(r'[-.:]+', '_', dt.now().isoformat())
        updated_run_map['role_validate_completed'] = False
        updated_run_map['role_create_completed'] = False
        updated_run_map['role_deploy_completed'] = False
        updated_run_map['role_remove_completed'] = False

        with open(run_map_file_path, 'w') as outfile:
            outfile.write('### This File Is Auto Generated, Do Not Edit ###\n')
            yaml.dump(updated_run_map, outfile, default_flow_style=False)

        results['run_map'] = updated_run_map

        # --- Manage model files (merged from manage_model_files plugin) ---
        results['end_host'] = False

        if results['save_previous']:
            files_dir = os.path.join(role_path, 'files')
            golden_file = os.path.join(
                files_dir, f'{fabric_name}_service_model_golden.json'
            )
            extended_file = os.path.join(
                files_dir, f'{fabric_name}_service_model_extended.json'
            )
            golden_prev = os.path.join(
                files_dir, f'{fabric_name}_service_model_golden_previous.json'
            )
            extended_prev = os.path.join(
                files_dir, f'{fabric_name}_service_model_extended_previous.json'
            )

            golden_exists = os.path.isfile(golden_file)
            extended_exists = os.path.isfile(extended_file)

            checksum_compare = results['validate_checksum_compare_enabled']
            model_diff_enabled = results['validate_model_diff_enabled']
            validate_only_run = results['validate_only_run']

            previous_golden_data = None
            previous_extended_data = None
            if model_diff_enabled:
                if golden_exists:
                    with open(golden_file) as f:
                        previous_golden_data = json.load(f)
                if extended_exists:
                    with open(extended_file) as f:
                        previous_extended_data = json.load(f)

            prev_golden_checksum = None
            prev_extended_checksum = None
            if checksum_compare:
                if golden_exists:
                    prev_golden_checksum = _file_checksum(golden_file)
                if extended_exists:
                    prev_extended_checksum = _file_checksum(extended_file)

            if golden_exists:
                shutil.move(golden_file, golden_prev)
            if extended_exists:
                shutil.move(extended_file, extended_prev)

            golden_content = json.dumps(
                results['model_golden'], indent=4, sort_keys=True
            )
            extended_content = json.dumps(
                results['model_extended'], indent=4, sort_keys=True
            )

            with open(golden_file, 'w') as f:
                f.write(golden_content)
            with open(extended_file, 'w') as f:
                f.write(extended_content)

            checksums_match = False
            if checksum_compare and prev_golden_checksum and prev_extended_checksum:
                curr_golden_checksum = _file_checksum(golden_file)
                curr_extended_checksum = _file_checksum(extended_file)
                checksums_match = (
                    prev_golden_checksum == curr_golden_checksum
                    and prev_extended_checksum == curr_extended_checksum
                )
                if checksums_match:
                    display.display(
                        'No model changes detected (checksums match)', color='green'
                    )

            if model_diff_enabled and not checksums_match:
                current_golden_data = json.loads(golden_content)
                current_extended_data = json.loads(extended_content)
                if previous_golden_data is not None:
                    display.display('--- Model Diff (Golden) ---', color='cyan')
                    _display_diff(previous_golden_data, current_golden_data)
                if previous_extended_data is not None:
                    display.display('--- Model Diff (Extended) ---', color='cyan')
                    _display_diff(previous_extended_data, current_extended_data)

            if bool(force_run_all):
                pattern = os.path.join(
                    files_dir, f'{fabric_name}_service_model*_previous.json'
                )
                for f_path in glob.glob(pattern):
                    os.remove(f_path)
                    display.display(f'Removed: {f_path}')

            # Mark validate completed always
            _mark_run_map(run_map_file_path, 'role_validate_completed')

            if checksums_match or validate_only_run:
                _mark_run_map(run_map_file_path, 'role_all_completed')
                if checksums_match:
                    results['end_host'] = True
        else:
            # No save_previous - just mark validate completed
            _mark_run_map(run_map_file_path, 'role_validate_completed')

        results['ansible_facts'] = {
            'data_model': results['model_golden'],
            'data_model_extended': results['model_extended'],
            'defaults': results['defaults'],
            'check_roles': {'save_previous': results['save_previous']},
            'run_map_read_result': {
                'diff_run': results['diff_run'],
                'validate_only_run': results['validate_only_run'],
            },
            'validate_checksum_compare_enabled': results[
                'validate_checksum_compare_enabled'
            ],
            'validate_model_diff_enabled': results['validate_model_diff_enabled'],
        }

        return results


def _file_checksum(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def _mark_run_map(run_map_file_path, stage):
    import yaml as _yaml

    if not os.path.exists(run_map_file_path):
        return
    with open(run_map_file_path, 'r') as f:
        data = _yaml.safe_load(f)
    if stage == 'role_all_completed':
        data['role_validate_completed'] = True
        data['role_create_completed'] = True
        data['role_deploy_completed'] = True
        data['role_remove_completed'] = True
    else:
        data[stage] = True
    with open(run_map_file_path, 'w') as f:
        f.write('### This File Is Auto Generated, Do Not Edit ###\n')
        _yaml.dump(data, f, default_flow_style=False)


def _display_diff(before, after):
    before_lines = json.dumps(before, indent=2, sort_keys=True).splitlines()
    after_lines = json.dumps(after, indent=2, sort_keys=True).splitlines()
    diff = difflib.unified_diff(before_lines, after_lines, lineterm='', n=3)
    diff_output = '\n'.join(diff)
    if diff_output:
        display.display(diff_output)
    else:
        display.display('(no differences)')


def _prepare_service_model(
    results, data_model, default_values, host_name, hostvars, templates_path
):
    import importlib
    import pathlib
    import copy

    sm_data = data_model
    results['model_extended'] = copy.deepcopy(sm_data)

    glob_plugin_path = os.path.join(os.path.dirname(__file__), 'prepare_plugins')
    full_plugin_path = (
        'ansible_collections.cisco.nac_dc_vxlan.plugins.action.common.prepare_plugins'
    )
    plugin_prefix = 'prep*.py'

    prepare_libs = set(
        x.stem for x in pathlib.Path(glob_plugin_path).glob(plugin_prefix)
    )
    dict_of_plugins = {}
    for lib in prepare_libs:
        plugin_name = f'{full_plugin_path}.{lib}'
        plugin_module = importlib.import_module(plugin_name, '.')
        dict_of_plugins[lib] = plugin_module

    plugin_keys = sorted(dict_of_plugins)
    for plugin_name in plugin_keys:
        if hasattr(dict_of_plugins[plugin_name].PreparePlugin(), 'keys'):
            if not isinstance(dict_of_plugins[plugin_name].PreparePlugin().keys, list):
                results['failed'] = True
                results['msg'] = f'Plugin {plugin_name} must have a list of keys'
        else:
            results['failed'] = True
            results['msg'] = f'Plugin {plugin_name} must have a list of keys'

        results = (
            dict_of_plugins[plugin_name]
            .PreparePlugin(
                host_name=host_name,
                hostvars=hostvars,
                default_values=default_values,
                templates_path=templates_path,
                results=results,
            )
            .prepare()
        )

        if results.get('failed'):
            break

    if results.get('failed'):
        results_copy = results.copy()
        for key in list(results_copy.keys()):
            if key.startswith('model'):
                del results[key]
    else:
        results['model_golden'] = sm_data

    return results


def _merge_dicts(d1, d2):
    """Deep merge d2 into d1."""
    for k, v in d2.items():
        if k in d1 and isinstance(d1[k], dict) and isinstance(v, dict):
            d1[k] = _merge_dicts(d1[k], v)
        else:
            d1[k] = v
    return d1

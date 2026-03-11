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

"""
Build Resource Data — Consolidated Template→Render→Diff→Flag pipeline for all fabric types.

Replaces the dtc/common role's per-fabric-type sub_main_*.yml files and
~50 individual resource task files with a single data-driven action plugin.

Resource type metadata is loaded from objects/resource_types.yml.
Each resource declares its applicable fabric_types — the plugin filters
to only process entries matching the current fabric.

Implements the same Template→Render→Diff→Flag cycle as the original YAML tasks:
  1. Backup previous rendered file (if exists)
  2. Render Jinja2 template to output file
  3. Load rendered YAML data into variable
  4. Run structural diff (diff_compare) for resources that support it
  5. Run MD5 diff (diff_model_changes) to detect any changes
  6. Set change flag if data changed and save_previous is active

Entries with template: null are non-template steps dispatched to
internal methods by resource name:
  - child_fabrics:    Prepare MSD child fabric associations
  - interface_all:    Aggregate all interface types into combined lists
  - check_msd_child:  Validate overlay not managed from MSD child fabric
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import hashlib
import os
import re
import shutil

import yaml

from ansible.plugins.action import ActionBase
from ansible.plugins.loader import action_loader
from ansible.utils.display import Display

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.registry_loader import (
    RegistryLoader,
)

display = Display()


class ResourceDataBuilder:
    """
    Core Template→Render→Diff→Flag pipeline logic.

    Iterates through resource_types.yml filtered by fabric_type,
    rendering templates, detecting changes, and collecting resource
    data for downstream create/remove plugins.
    """

    def __init__(self, params, action_module, task_vars, tmp=None):
        self.fabric_type = params['fabric_type']
        self.fabric_name = params['fabric_name']
        self.data_model = params['data_model']
        self.role_path = params['role_path']
        self.run_map_diff_run = params.get('run_map_diff_run', True)
        self.force_run_all = params.get('force_run_all', False)
        self.check_roles = params.get('check_roles', {})

        self.action_module = action_module
        self.task_vars = task_vars
        self.tmp = tmp

        # Load registries
        collection_path = RegistryLoader.get_collection_path()
        self.resource_types = RegistryLoader.load(collection_path, 'resource_types').get('resource_types', {})
        self.fabric_types = RegistryLoader.load(collection_path, 'fabric_types').get('fabric_types', {})

        # Get fabric type config
        self.fabric_type_config = self.fabric_types.get(self.fabric_type, {})
        self.file_subdir = self.fabric_type_config.get('file_subdir', '')
        self.namespace = self.fabric_type_config.get('namespace', '')

        # Output path: {role_path}/files/{file_subdir}/{fabric_name}/
        self.output_path = os.path.join(
            self.role_path, 'files', self.file_subdir, self.fabric_name
        )

        # Collected results
        self.resource_data = {}
        self.change_flags = {}
        self.diff_results = {}

    def build(self):
        """
        Execute the resource pipeline for the current fabric type.

        Iterates resource_types.yml in order, processing only entries
        whose fabric_types list includes the current fabric type.

        Returns:
            dict with:
              - 'resource_data': Dict of rendered data keyed by resource_name
              - 'change_flags': Dict of change flag states
              - 'diff_results': Dict of structural diff results
              - 'namespace': Fabric type namespace name
              - 'failed': Boolean
              - 'msg': Summary message
        """
        # Cleanup output directory if not a diff run
        if not self.run_map_diff_run or self.force_run_all:
            self._cleanup_files()

        # Ensure output directory exists
        os.makedirs(self.output_path, exist_ok=True)

        step_results = []

        for resource_name, rt in self.resource_types.items():
            # Filter by fabric type
            applicable_fabrics = rt.get('fabric_types', [])
            if self.fabric_type not in applicable_fabrics:
                continue

            template = rt.get('template')

            # ── Non-template step: dispatch to internal method ────────
            if template is None:
                method_name = f'_{resource_name}'
                try:
                    method = getattr(self, method_name)
                    result = method(rt)
                    step_results.append({
                        'resource_name': resource_name,
                        'status': 'ok',
                        'result': result,
                    })
                    if isinstance(result, dict) and result.get('failed'):
                        return {
                            'resource_data': self.resource_data,
                            'change_flags': self.change_flags,
                            'diff_results': self.diff_results,
                            'namespace': self.namespace,
                            'results': step_results,
                            'failed': True,
                            'msg': result.get('msg', f"Step '{resource_name}' failed"),
                        }
                except AttributeError:
                    step_results.append({
                        'resource_name': resource_name,
                        'status': 'failed',
                        'reason': f"Internal method '{method_name}' not found",
                    })
                    return {
                        'resource_data': self.resource_data,
                        'change_flags': self.change_flags,
                        'diff_results': self.diff_results,
                        'namespace': self.namespace,
                        'results': step_results,
                        'failed': True,
                        'msg': f"Internal method '{method_name}' not found on ResourceDataBuilder",
                    }
                continue

            # ── Resolve template (apply fabric-specific override) ─────
            template_overrides = rt.get('template_overrides', {})
            if self.fabric_type in template_overrides:
                template = template_overrides[self.fabric_type]

            # ── Standard resource build ───────────────────────────────
            result = self._build_resource(resource_name, rt, template)
            step_results.append({
                'resource_name': resource_name,
                'status': 'ok' if not result.get('failed') else 'failed',
                'result': result,
            })

            if result.get('failed'):
                return {
                    'resource_data': self.resource_data,
                    'change_flags': self.change_flags,
                    'diff_results': self.diff_results,
                    'namespace': self.namespace,
                    'results': step_results,
                    'failed': True,
                    'msg': f"Build failed at step '{resource_name}': {result.get('msg', '')}",
                }

        # Compute aggregate change flag
        self.change_flags['changes_detected_any'] = any(self.change_flags.values())

        return {
            'resource_data': self.resource_data,
            'change_flags': self.change_flags,
            'diff_results': self.diff_results,
            'namespace': self.namespace,
            'results': step_results,
            'failed': False,
            'msg': f"Common pipeline completed for {self.fabric_type} fabric '{self.fabric_name}'",
        }

    # ══════════════════════════════════════════════════════════════════════════
    # Core Build Cycle
    # ══════════════════════════════════════════════════════════════════════════

    def _build_resource(self, resource_name, rt, template):
        """
        Execute the Template→Render→Diff→Flag cycle for one resource.

        Args:
            resource_name: Logical name of the resource.
            rt: Resource type config dict from resource_types.yml.
            template: Template path (may be overridden by pipeline step).

        Returns:
            dict with build result.
        """
        output_file = rt['output_file']
        change_flag = rt['change_flag']
        diff_compare = rt.get('diff_compare', False)
        var_name = rt.get('var_name', resource_name)

        output_file_path = os.path.join(self.output_path, output_file)
        old_file_path = output_file_path + '.old'

        # ── Step 1: Backup previous file ──────────────────────────────
        if os.path.exists(output_file_path):
            shutil.copy2(output_file_path, old_file_path)
            os.remove(output_file_path)

        # ── Step 2: Execute pre-hooks ─────────────────────────────────
        pre_hook_data = {}
        for hook in rt.get('pre_hooks', []):
            hook_result = self._execute_hook(hook)
            pre_hook_data[hook] = hook_result

        # ── Step 3: Render template ───────────────────────────────────
        try:
            self._render_template(template, output_file_path)
        except Exception as e:
            return {
                'failed': True,
                'msg': f"Template rendering failed for {resource_name}: {str(e)}",
            }

        # ── Step 4: Load rendered data ────────────────────────────────
        data = self._load_yaml(output_file_path)

        # ── Step 5: Execute post-hooks ────────────────────────────────
        for hook in rt.get('post_hooks', []):
            hook_result = self._execute_post_hook(hook, resource_name, data)
            if hook_result is not None:
                pre_hook_data[hook] = hook_result

        # ── Step 6: Structural diff (diff_compare) ───────────────────
        diff_result = None
        if diff_compare:
            diff_result = self._run_diff_compare(old_file_path, output_file_path)
            self.diff_results[resource_name] = diff_result

        # ── Step 7: MD5 diff for change detection ─────────────────────
        file_changed = self._run_diff_model_changes(old_file_path, output_file_path)

        # ── Step 8: Set change flag ───────────────────────────────────
        if change_flag and file_changed and self.check_roles.get('save_previous', False):
            self.change_flags[change_flag] = True

        # ── Store resource data ───────────────────────────────────────
        # module_data is the authoritative data for downstream NDFC module calls.
        # Default is the raw rendered template data. Post-hooks can override this
        # by returning a 'module_data' key in their result dict (convention).
        resource_entry = {'data': data, 'module_data': data, 'var_name': var_name}
        if diff_result is not None:
            resource_entry['diff'] = diff_result

        # Store hook data alongside resource data
        if pre_hook_data:
            resource_entry['hook_data'] = pre_hook_data
            # Convention: if any post-hook returned 'module_data', use it as the
            # authoritative data for downstream modules (e.g., credential-enriched
            # inventory from get_credentials).
            for hook_result in pre_hook_data.values():
                if isinstance(hook_result, dict) and 'module_data' in hook_result:
                    resource_entry['module_data'] = hook_result['module_data']
                    break

        self.resource_data[resource_name] = resource_entry

        display.v(
            f"COMMON [{self.fabric_name}] Built {resource_name}: "
            f"items={len(data) if isinstance(data, list) else '?'}, "
            f"changed={file_changed}"
        )

        return {'failed': False, 'changed': file_changed}

    # ══════════════════════════════════════════════════════════════════════════
    # Template Rendering
    # ══════════════════════════════════════════════════════════════════════════

    def _render_template(self, template_name, output_path):
        """
        Render a Jinja2 template using Ansible's Templar.

        Uses Ansible's Templar to render Jinja2 templates with all available
        task variables. The template is loaded from the role's templates
        directory.

        Args:
            template_name: Template path relative to role templates dir.
            output_path: Absolute path for the rendered output file.
        """
        from jinja2 import ChoiceLoader, FileSystemLoader

        template_dir = os.path.join(self.role_path, 'templates')
        template_path = os.path.join(template_dir, template_name)

        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path) as f:
            template_content = f.read()

        templar = self.action_module._templar
        original_loader = templar.environment.loader

        # Add role templates dir to Jinja2 loader for {% include %} and {% import %}
        new_loader = ChoiceLoader([
            FileSystemLoader(template_dir),
            original_loader,
        ])
        templar.environment.loader = new_loader

        try:
            old_vars = templar.available_variables
            templar.available_variables = self.task_vars

            rendered = templar.template(
                template_content,
                preserve_trailing_newlines=True,
                convert_data=False,
            )
        finally:
            templar.environment.loader = original_loader
            templar.available_variables = old_vars

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(rendered)

    def _load_yaml(self, path):
        """Load a YAML file and return its contents, or empty list."""
        if not os.path.exists(path):
            return []
        with open(path) as f:
            data = yaml.safe_load(f)
        return data if data else []

    # ══════════════════════════════════════════════════════════════════════════
    # Diff Operations
    # ══════════════════════════════════════════════════════════════════════════

    def _run_diff_model_changes(self, old_path, current_path):
        """
        Compare previous and current files via MD5 hash (with omit placeholder normalization).

        Replicates the logic from dtc.diff_model_changes action plugin.
        If files are identical, removes the .old backup file.

        Args:
            old_path: Path to the previous file (.old).
            current_path: Path to the current file.

        Returns:
            True if file data changed, False otherwise.
        """
        if not os.path.exists(old_path):
            return True

        with open(old_path, 'r') as f:
            data_previous = f.read()
        with open(current_path, 'r') as f:
            data_current = f.read()

        md5_prev = hashlib.md5(data_previous.encode()).hexdigest()
        md5_curr = hashlib.md5(data_current.encode()).hexdigest()

        if md5_prev == md5_curr:
            os.remove(old_path)
            return False

        # Normalize omit placeholders and compare again
        pattern = r'__omit_place_holder__\S+'
        data_previous = re.sub(pattern, 'NORMALIZED', data_previous, flags=re.MULTILINE)
        data_current = re.sub(pattern, 'NORMALIZED', data_current, flags=re.MULTILINE)

        md5_prev = hashlib.md5(data_previous.encode()).hexdigest()
        md5_curr = hashlib.md5(data_current.encode()).hexdigest()

        if md5_prev == md5_curr:
            os.remove(old_path)
            return False

        return True

    def _run_diff_compare(self, old_path, new_path):
        """
        Run structural diff comparison for targeted create/remove data.

        Delegates to the existing diff_compare action plugin to compute
        updated, removed, and equal item lists.

        Args:
            old_path: Path to the previous file (.old).
            new_path: Path to the current file.

        Returns:
            Dict with 'updated', 'removed', 'equal' lists.
        """
        result = self._run_action_plugin(
            "cisco.nac_dc_vxlan.dtc.diff_compare",
            {"old_file": old_path, "new_file": new_path},
        )
        return result

    # ══════════════════════════════════════════════════════════════════════════
    # Action Plugin Invocation
    # ══════════════════════════════════════════════════════════════════════════

    def _run_action_plugin(self, action_name, args):
        """
        Instantiate and run another action plugin by fully-qualified name.

        Used for hooks like get_poap_data and get_credentials which are
        action plugins (not modules) and cannot be called via _execute_module.
        """
        task = self.action_module._task.copy()
        task.action = action_name
        task.args = args

        action = action_loader.get(
            action_name,
            task=task,
            connection=self.action_module._connection,
            play_context=self.action_module._play_context,
            loader=self.action_module._loader,
            templar=self.action_module._templar,
            shared_loader_obj=self.action_module._shared_loader_obj,
        )
        return action.run(task_vars=self.task_vars)

    # ══════════════════════════════════════════════════════════════════════════
    # Hooks
    # ══════════════════════════════════════════════════════════════════════════

    def _execute_hook(self, hook_name):
        """
        Execute a pre-hook before template rendering.

        Currently supports:
          - get_poap_data: Retrieve POAP data from POAP-enabled devices.

        Args:
            hook_name: Name of the hook to execute.

        Returns:
            Hook result dict.
        """
        if hook_name == 'get_poap_data':
            result = self._run_action_plugin(
                "cisco.nac_dc_vxlan.dtc.get_poap_data",
                {"data_model": self.data_model},
            )
            # Store poap_data in task_vars for template rendering
            self.task_vars['poap_data'] = result
            return result

        display.warning(f"Unknown pre-hook: {hook_name}")
        return {}

    def _execute_post_hook(self, hook_name, resource_name, data):
        """
        Execute a post-hook after template rendering and data loading.

        Currently supports:
          - get_credentials: Retrieve NDFC device credentials and update
            inventory config.

        Args:
            hook_name: Name of the hook to execute.
            resource_name: Name of the resource being built.
            data: Rendered data from the template.

        Returns:
            Updated data dict, or None if hook doesn't modify data.
        """
        if hook_name == 'get_credentials':
            result = self._run_action_plugin(
                "cisco.nac_dc_vxlan.common.get_credentials",
                {"inv_list": data, "data_model": self.data_model},
            )
            if result.get('retrieve_failed'):
                raise RuntimeError(f"Credential retrieval failed: {result}")
            return result

        display.warning(f"Unknown post-hook: {hook_name}")
        return None

    # ══════════════════════════════════════════════════════════════════════════
    # File Operations
    # ══════════════════════════════════════════════════════════════════════════

    def _cleanup_files(self):
        """
        Remove all files from the output directory for a clean full run.

        Matches the original cleanup_files.yml behavior: delete directory
        contents and recreate the empty directory.
        """
        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path)
        os.makedirs(self.output_path, exist_ok=True)

    # ══════════════════════════════════════════════════════════════════════════
    # Internal Methods (called from pipeline via '_' prefix in resource_name)
    # ══════════════════════════════════════════════════════════════════════════

    def _interface_all(self, rt):
        """
        Aggregate all individual interface type data into combined lists.

        Produces two aggregated lists:
          - interface_all_create: All interfaces EXCEPT breakout_preprov
            (used by create pipeline with state: merged)
          - interface_all_remove_overridden: ALL interfaces including breakout_preprov
            (used by remove pipeline with state: overridden)

        Also runs diff_compare on the aggregated list for targeted operations.
        """
        interface_types_create = [
            'interface_breakout',
            'interface_trunk',
            'interface_routed',
            'sub_interface_routed',
            'interface_access',
            'interface_trunk_po',
            'interface_access_po',
            'interface_po_routed',
            'interface_loopback',
            'interface_dot1q',
            'interface_vpc',
        ]

        interface_types_remove = [
            'interface_breakout',
            'interface_breakout_preprov',
            'interface_trunk',
            'interface_routed',
            'sub_interface_routed',
            'interface_access',
            'interface_trunk_po',
            'interface_access_po',
            'interface_po_routed',
            'interface_loopback',
            'interface_dot1q',
            'interface_vpc',
        ]

        # Aggregate create list (no breakout_preprov)
        create_list = []
        for itype in interface_types_create:
            entry = self.resource_data.get(itype, {})
            data = entry.get('data', []) if isinstance(entry, dict) else []
            create_list.extend(data)

        # Aggregate remove/overridden list (includes breakout_preprov)
        remove_list = []
        for itype in interface_types_remove:
            entry = self.resource_data.get(itype, {})
            data = entry.get('data', []) if isinstance(entry, dict) else []
            remove_list.extend(data)

        # Write aggregated file for diff comparison
        output_file = os.path.join(self.output_path, 'ndfc_interface_all.yml')
        old_file = output_file + '.old'

        # Backup previous
        if os.path.exists(output_file):
            shutil.copy2(output_file, old_file)
            os.remove(output_file)

        # Write current
        with open(output_file, 'w') as f:
            yaml.dump(create_list, f, default_flow_style=False)

        # Run structural diff
        diff_result = self._run_diff_compare(old_file, output_file)

        # Run MD5 diff
        file_changed = self._run_diff_model_changes(old_file, output_file)

        # Set change flag
        if file_changed and self.check_roles.get('save_previous', False):
            self.change_flags['changes_detected_interfaces'] = True

        # Store aggregated data
        self.resource_data['interface_all'] = {
            'data': create_list,
            'data_overridden': remove_list,
            'diff': diff_result,
            'var_name': 'interface_all_create',
        }
        self.diff_results['interface_all'] = diff_result

        display.v(
            f"COMMON [{self.fabric_name}] Aggregated interface_all: "
            f"create={len(create_list)}, remove={len(remove_list)}, "
            f"changed={file_changed}"
        )

        return {'failed': False}

    def _child_fabrics(self, rt):
        """
        Prepare MSD child fabric association data.

        Delegates to the existing prepare_msite_child_fabrics_data plugin.
        This is not template-based — it queries the controller for fabric
        association information.
        """
        child_fabrics = self.data_model.get('vxlan', {}).get('multisite', {}).get('child_fabrics')

        if not child_fabrics:
            display.v(
                f"COMMON [{self.fabric_name}] No child fabrics defined, skipping"
            )
            return {'failed': False}

        result = self._run_action_plugin(
            "cisco.nac_dc_vxlan.dtc.prepare_msite_child_fabrics_data",
            {
                "parent_fabric": self.fabric_name,
                "parent_fabric_type": self.fabric_type,
                "child_fabrics": child_fabrics,
            },
        )

        self.resource_data['child_fabrics'] = {
            'data': result,
            'var_name': 'child_fabrics',
        }

        return result

    def _check_msd_child(self, rt):
        """
        Check if the current fabric is an active child in an MSD deployment.

        If the fabric is a child of an MSD parent, VRFs and Networks cannot
        be managed from the child fabric level — they must be managed from
        the MSD parent. This method fails the pipeline if the user attempts
        to manage overlay resources from a child fabric.
        """
        # Check if already determined
        is_child = self.task_vars.get('is_active_child_fabric')

        if is_child is None:
            # Query controller for MSD fabric associations
            result = self.action_module._execute_module(
                module_name="cisco.dcnm.dcnm_rest",
                module_args={
                    "method": "GET",
                    "path": (
                        "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control"
                        "/fabrics/msd/fabric-associations"
                    ),
                },
                task_vars=self.task_vars,
                tmp=self.tmp,
            )

            is_child = False
            try:
                associations = result.get('response', {}).get('DATA', [])
                if isinstance(associations, list):
                    for assoc in associations:
                        if (assoc.get('fabricName') == self.fabric_name and
                                assoc.get('fabricParent', 'None') != 'None'):
                            is_child = True
                            break
            except (KeyError, TypeError, IndexError):
                pass

            # Store for downstream use
            self.task_vars['is_active_child_fabric'] = is_child

        # Check for overlay data on child fabric
        vrf_entry = self.resource_data.get('vrfs', {})
        vrf_data = vrf_entry.get('data', []) if isinstance(vrf_entry, dict) else []

        net_entry = self.resource_data.get('networks', {})
        net_data = net_entry.get('data', []) if isinstance(net_entry, dict) else []

        if is_child and vrf_data:
            return {
                'failed': True,
                'msg': (
                    f"VRFs cannot be managed from fabric '{self.fabric_name}' "
                    f"as it is a child fabric part of a Multisite fabric."
                ),
            }

        if is_child and net_data:
            return {
                'failed': True,
                'msg': (
                    f"Networks cannot be managed from fabric '{self.fabric_name}' "
                    f"as it is a child fabric part of a Multisite fabric."
                ),
            }

        return {'failed': False, 'is_active_child_fabric': is_child}


class ActionModule(ActionBase):
    """
    Ansible ActionBase wrapper for build_resource_data.

    Handles parameter validation, error handling, and delegation
    to the ResourceDataBuilder domain class.
    """

    REQUIRED_PARAMS = [
        'fabric_type', 'fabric_name', 'data_model', 'role_path',
    ]

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        task_vars = task_vars or {}

        # Validate required parameters
        params = self._task.args
        missing = [p for p in self.REQUIRED_PARAMS if p not in params]
        if missing:
            results['failed'] = True
            results['msg'] = f"Missing required parameters: {missing}"
            return results

        try:
            builder = ResourceDataBuilder(params, self, task_vars, tmp)
            result = builder.build()

            results.update(result)
            if result.get('failed'):
                results['failed'] = True
            else:
                results['changed'] = any(
                    r.get('result', {}).get('changed', False)
                    for r in result.get('results', [])
                    if isinstance(r.get('result'), dict)
                )

        except Exception as e:
            results['failed'] = True
            results['msg'] = f"Build resource data failed: {str(e)}"

        return results

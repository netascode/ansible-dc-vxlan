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

import os
import re
import yaml
import shutil
import hashlib
import inspect

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase
from ansible.template import Templar
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.registry_loader import RegistryLoader

display = Display()

# Subdirectory mapping per fabric type for rendered output files
FABRIC_SUBDIR_MAP = {
    'VXLAN_EVPN': 'vxlan',
    'eBGP_VXLAN': 'vxlan',
    'ISN': 'isn',
    'MSD': 'msd',
    'MCFG': 'mcfg',
    'External': 'vxlan',
}

# Interface types that compose the interface_all aggregate
INTERFACE_TYPES = [
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


class ResourceBuilder:
    """
    Consolidates the Template→Render→Diff→Flag cycle for all resource types.

    Replaces the dtc/common role's sub_main_*.yml dispatch files and the
    ~25 individual task files under tasks/common/ and tasks/vxlan/ with a
    single data-driven pipeline.

    Resource type definitions are loaded from objects/resource_types.yml
    via the RegistryLoader utility. Adding a new resource type requires
    only editing that YAML file — no Python changes needed.

    The pipeline for each resource type is:
        1. Backup previous rendered file (if exists)
        2. Render Jinja2 template → YAML output file
        3. Load rendered data into memory
        4. MD5 diff check (with omit_placeholder normalization)
        5. Structural diff (if diff_compare is enabled)
        6. Update change detection flag
        7. Cleanup .old backup file
    """

    def __init__(self, params):
        self.class_name = self.__class__.__name__

        # Fabric parameters
        self.fabric_type = params['fabric_type']
        self.fabric_name = params['fabric_name']
        self.data_model = params['data_model']
        self.role_path = params['role_path']

        # Execution control parameters
        self.check_roles = params['check_roles']
        self.force_run_all = params['force_run_all']
        self.run_map_diff_run = params['run_map_diff_run']

        # Ansible execution context
        self.task_vars = params['task_vars']
        self.tmp = params['tmp']
        self.action_module = params['action_module']

        # Load resource types registry from external YAML
        self.collection_path = RegistryLoader.get_collection_path()
        registry = RegistryLoader.load(self.collection_path, 'resource_types')
        self.resource_types = registry.get('resource_types', {})

        # Change detection flags — built up during the build process
        self.change_flags = {}

        # Compute output base path for rendered files
        self.fabric_subdir = FABRIC_SUBDIR_MAP.get(self.fabric_type, 'vxlan')
        self.output_path = os.path.join(
            self.role_path, 'files', self.fabric_subdir, self.fabric_name
        )

        # Ensure output directory exists
        os.makedirs(self.output_path, exist_ok=True)

    def build_all(self):
        """
        Build all resource data for the given fabric type.

        Iterates over all resource types from the registry that apply to
        the current fabric type, executing the full template→diff→flag
        pipeline for each one.

        Returns:
            dict with keys:
                - resource_data: {resource_name: {data, changed, diff}}
                - change_flags: {flag_name: bool}
        """
        method_name = inspect.stack()[0][3]
        display.banner(
            f"{self.class_name}.{method_name}() "
            f"Fabric: ({self.fabric_name}) Type: ({self.fabric_type})"
        )

        results = {}

        # Handle file cleanup for non-diff runs
        if not self.run_map_diff_run or self.force_run_all:
            self._cleanup_previous_run()

        # Filter resource types applicable to this fabric type
        applicable_resources = [
            (name, cfg) for name, cfg in self.resource_types.items()
            if self.fabric_type in cfg.get('fabric_types', [])
        ]

        display.v(
            f"{self.class_name}: Building {len(applicable_resources)} resource types "
            f"for fabric type {self.fabric_type}"
        )

        # Execute the pipeline for each applicable resource type
        for resource_name, config in applicable_resources:
            display.v(f"{self.class_name}: Processing resource '{resource_name}'")
            result = self._build_single_resource(resource_name, config)
            results[resource_name] = result

        # Build composite interface_all from individual interface results
        if self.fabric_type in ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External']:
            display.v(f"{self.class_name}: Building composite interface_all")
            results['interface_all'] = self._build_interface_all(results)

        # Compute the changes_detected_any aggregate flag
        self.change_flags['changes_detected_any'] = any(
            v for k, v in self.change_flags.items()
            if k != 'changes_detected_any'
        )

        return {
            'resource_data': results,
            'change_flags': self.change_flags,
        }

    def _build_single_resource(self, resource_name, config):
        """
        Execute the full Template→Render→Diff→Flag pipeline for one resource.

        This replaces the ~50 lines of YAML that each task file in
        common/ndfc_*.yml implements.

        Args:
            resource_name: Logical name of the resource (e.g., 'fabric', 'inventory')
            config: Resource type configuration from the registry

        Returns:
            dict with keys: data, changed, diff
        """
        template_name = config['template']
        output_file = config['output_file']
        change_flag = config.get('change_flag')
        diff_compare = config.get('diff_compare', False)

        file_path = os.path.join(self.output_path, output_file)
        old_path = f"{file_path}.old"

        # 1. Backup previous file (if exists)
        self._backup_file(file_path, old_path)

        # 2. Render Jinja2 template → YAML output file
        self._render_template(template_name, file_path)

        # 3. Load rendered data into memory
        resource_data = self._load_yaml_file(file_path)

        # 4. MD5 diff check
        changed = self._check_md5_diff(old_path, file_path)

        # 5. Update change detection flag
        if changed and change_flag:
            self.change_flags[change_flag] = True
            display.v(f"{self.class_name}: Change detected for '{resource_name}' -> {change_flag} = True")
        elif change_flag and change_flag not in self.change_flags:
            self.change_flags[change_flag] = False

        # 6. Structural diff (if enabled and .old file exists)
        diff_result = None
        if diff_compare and os.path.exists(old_path):
            diff_result = self._structural_diff(old_path, file_path)

        # 7. Cleanup .old file if no changes
        self._cleanup_old(old_path, changed)

        return {
            'data': resource_data,
            'changed': changed,
            'diff': diff_result,
        }

    def _build_interface_all(self, results):
        """
        Compose the interface_all list from individual interface results.

        Replaces the ndfc_interface_all.yml task file which aggregates all
        interface types into a single list for create and remove operations.

        Args:
            results: Dict of {resource_name: {data, changed, diff}} from build pipeline

        Returns:
            dict with keys: data_create, data_remove_overridden, changed, diff
        """
        all_create = []
        all_remove_overridden = []

        for itype in INTERFACE_TYPES:
            if itype in results:
                data = results[itype].get('data', [])
                if isinstance(data, list):
                    all_create.extend(data)
                    all_remove_overridden.extend(data)

        # Write composite to file for structural diff
        composite_file = os.path.join(self.output_path, 'ndfc_interface_all.yml')
        composite_old = f"{composite_file}.old"

        # Backup existing composite
        self._backup_file(composite_file, composite_old)

        # Write new composite
        self._write_yaml_file(composite_file, all_create)

        # MD5 diff on composite
        composite_changed = self._check_md5_diff(composite_old, composite_file)

        if composite_changed:
            self.change_flags['changes_detected_interfaces'] = True

        # Structural diff on composite
        diff_result = None
        if os.path.exists(composite_old):
            diff_result = self._structural_diff(composite_old, composite_file)

        self._cleanup_old(composite_old, composite_changed)

        return {
            'data_create': all_create,
            'data_remove_overridden': all_remove_overridden,
            'changed': composite_changed,
            'diff': diff_result,
        }

    # =========================================================================
    # Template Rendering
    # =========================================================================

    def _render_template(self, template_name, output_path):
        """
        Render a Jinja2 template using Ansible's Templar.

        Uses Ansible's Templar directly to render the Jinja2 template
        with the full task_vars context (filters, lookups, variables).
        This approach is correct for action plugins — the template module
        is itself an action plugin and cannot be invoked via _execute_module
        (which expects a module script with a Python interpreter line).

        Args:
            template_name: Name of the Jinja2 template file (e.g., 'ndfc_fabric.j2')
            output_path: Full path to write the rendered output
        """
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Find the template source path
        template_src = self._find_template(template_name)

        # Determine the templates directory that contains this template.
        # This is needed so that Jinja2 {% include %} / {% import %} directives
        # with paths like '/ndfc_fabric/dc_vxlan_fabric/...' resolve correctly
        # against the role's (or collection's) templates directory.
        templates_dir = os.path.join(self.role_path, 'templates')
        if not template_src.startswith(templates_dir):
            templates_dir = os.path.join(self.collection_path, 'templates')

        # Read the raw Jinja2 template
        with open(template_src, 'r') as f:
            template_content = f.read()

        # Set the loader's basedir to the templates directory so that
        # {% include %} paths resolve correctly, then restore it after.
        loader = self.action_module._loader
        original_basedir = loader.get_basedir()
        loader.set_basedir(templates_dir)

        try:
            # Render using Ansible's Templar with the full task_vars context
            templar = Templar(
                loader=loader,
                variables=self.task_vars,
            )
            rendered = templar.template(template_content)
        except Exception as e:
            raise RuntimeError(
                f"Template rendering failed for '{template_name}': {str(e)}"
            )
        finally:
            # Always restore the original basedir
            loader.set_basedir(original_basedir)

        # Write rendered output to file
        with open(output_path, 'w') as f:
            f.write(rendered)
        os.chmod(output_path, 0o644)

    def _find_template(self, template_name):
        """
        Locate a Jinja2 template file.

        Searches in the role's templates directory first (standard Ansible
        role convention), then falls back to the collection's templates dir.

        Args:
            template_name: Name of the template file

        Returns:
            Absolute path to the template file

        Raises:
            FileNotFoundError: If the template cannot be found
        """
        # Check role templates directory first
        role_template = os.path.join(self.role_path, 'templates', template_name)
        if os.path.exists(role_template):
            return role_template

        # Check collection-level templates directory
        collection_template = os.path.join(self.collection_path, 'templates', template_name)
        if os.path.exists(collection_template):
            return collection_template

        raise FileNotFoundError(
            f"Template '{template_name}' not found in role or collection templates directories. "
            f"Searched: {role_template}, {collection_template}"
        )

    # =========================================================================
    # Diff & Change Detection
    # =========================================================================

    def _check_md5_diff(self, old_path, new_path):
        """
        MD5-based change detection with omit_placeholder normalization.

        Replicates the logic from diff_model_changes.py which normalizes
        __omit_place_holder__ strings before comparing file hashes.

        Args:
            old_path: Path to the previous file (.old backup)
            new_path: Path to the current file

        Returns:
            True if files differ, False if identical
        """
        if not os.path.exists(old_path):
            return True

        with open(old_path, 'r') as f:
            old_data = f.read()
        with open(new_path, 'r') as f:
            new_data = f.read()

        # First compare raw hashes
        old_md5 = hashlib.md5(old_data.encode()).hexdigest()
        new_md5 = hashlib.md5(new_data.encode()).hexdigest()
        if old_md5 == new_md5:
            return False

        # If raw hashes differ, normalize omit placeholders and re-compare
        pattern = r'__omit_place_holder__\S+'
        old_normalized = re.sub(pattern, 'NORMALIZED', old_data, flags=re.MULTILINE)
        new_normalized = re.sub(pattern, 'NORMALIZED', new_data, flags=re.MULTILINE)

        old_md5 = hashlib.md5(old_normalized.encode()).hexdigest()
        new_md5 = hashlib.md5(new_normalized.encode()).hexdigest()

        return old_md5 != new_md5

    def _structural_diff(self, old_path, new_path):
        """
        Perform a structural diff using the existing diff_compare plugin.

        Delegates to the cisco.nac_dc_vxlan.dtc.diff_compare action plugin
        to compute updated/removed/equal item lists for targeted
        create and remove operations.

        Args:
            old_path: Path to the previous file
            new_path: Path to the current file

        Returns:
            dict with keys: updated, removed, equal
        """
        result = self.action_module._execute_module(
            module_name='cisco.nac_dc_vxlan.dtc.diff_compare',
            module_args={
                'old_file': old_path,
                'new_file': new_path,
            },
            task_vars=self.task_vars,
            tmp=self.tmp,
        )

        if result.get('failed'):
            display.warning(
                f"Structural diff failed for {new_path}: {result.get('msg', 'unknown error')}"
            )
            return {'updated': [], 'removed': [], 'equal': []}

        return result.get('compare', {'updated': [], 'removed': [], 'equal': []})

    # =========================================================================
    # File Utilities
    # =========================================================================

    def _backup_file(self, file_path, old_path):
        """Backup existing file to .old extension and remove original."""
        if os.path.exists(file_path):
            shutil.copy2(file_path, old_path)
            os.remove(file_path)

    def _cleanup_old(self, old_path, changed):
        """Remove .old backup file if no changes were detected."""
        if not changed and os.path.exists(old_path):
            os.remove(old_path)

    def _cleanup_previous_run(self):
        """
        Remove all files from the previous run when diff_run is not active.

        This replicates the cleanup_files.yml task that runs at the beginning
        of the common role when a full (non-diff) run is triggered.
        """
        if os.path.isdir(self.output_path):
            for filename in os.listdir(self.output_path):
                filepath = os.path.join(self.output_path, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    display.v(f"{self.class_name}: Cleaned up {filepath}")

    def _load_yaml_file(self, file_path):
        """Load and return YAML data from a file."""
        if not os.path.exists(file_path):
            return []
        with open(file_path, 'r') as f:
            return yaml.safe_load(f) or []

    def _write_yaml_file(self, file_path, data):
        """Write data as YAML to a file."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)


class ActionModule(ActionBase):
    """
    Action plugin: build_resource_data

    Consolidates the Template→Render→Diff→Flag cycle for all resource types
    into a single action plugin call, replacing the dtc/common role's
    ~25 task files and ~6 sub_main dispatch files.

    Parameters (from task args):
        fabric_type:      Fabric type (VXLAN_EVPN, eBGP_VXLAN, ISN, MSD, MCFG, External)
        fabric_name:      Name of the fabric
        data_model:       Extended data model (data_model_extended)
        role_path:        Path to the common role
        check_roles:      Check roles configuration
        force_run_all:    Force full run regardless of diff state
        run_map_diff_run: Whether diff-based run is active

    Returns:
        resource_data:  {resource_name: {data, changed, diff}} for all applicable resources
        change_flags:   {flag_name: bool} with change detection state
    """

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False

        # Validate required parameters
        required_params = [
            'fabric_type', 'fabric_name', 'data_model',
            'role_path', 'check_roles',
        ]
        for param in required_params:
            if self._task.args.get(param) is None:
                results['failed'] = True
                results['msg'] = f"Missing required parameter '{param}'"
                return results

        # Build params dict matching the existing plugin conventions
        params = {
            'fabric_type': self._task.args['fabric_type'],
            'fabric_name': self._task.args['fabric_name'],
            'data_model': self._task.args['data_model'],
            'role_path': self._task.args['role_path'],
            'check_roles': self._task.args['check_roles'],
            'force_run_all': self._task.args.get('force_run_all', False),
            'run_map_diff_run': self._task.args.get('run_map_diff_run', True),
            'task_vars': task_vars,
            'tmp': tmp,
            'action_module': self,
        }

        try:
            builder = ResourceBuilder(params)
            build_result = builder.build_all()

            results['resource_data'] = build_result['resource_data']
            results['change_flags'] = build_result['change_flags']

        except FileNotFoundError as e:
            results['failed'] = True
            results['msg'] = f"Resource build failed — file not found: {str(e)}"
        except RuntimeError as e:
            results['failed'] = True
            results['msg'] = f"Resource build failed: {str(e)}"
        except Exception as e:
            results['failed'] = True
            results['msg'] = f"Unexpected error during resource build: {type(e).__name__}: {str(e)}"

        return results

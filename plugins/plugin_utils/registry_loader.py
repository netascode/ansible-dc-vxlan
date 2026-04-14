# Copyright (c) 2026 Cisco Systems, Inc. and its affiliates
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
Registry Loader — Shared YAML registry loader with LRU cache and validation.

Provides a single entry point for all DTC action plugins to load their
data-driven configuration from external YAML registry files under resources/.

Includes three validation capabilities:
  1. Cross-reference validation — pipeline resource_names vs resource_types keys
  2. Pipeline symmetry validation — create/remove step correspondence
  3. Schema validation — required fields check to catch YAML typos

Usage:
    from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.registry_loader import RegistryLoader

    collection_path = RegistryLoader.get_collection_path()
    resource_types = RegistryLoader.load(collection_path, 'resource_types')

    # Validate all registries at startup
    errors = RegistryLoader.validate_all(collection_path)
    if errors:
        raise ValueError(f"Registry validation failed: {errors}")
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import yaml
from functools import lru_cache

from ansible.utils.display import Display

display = Display()


# ══════════════════════════════════════════════════════════════════════════════
# Schema Definitions — Required fields for each registry entry type
# ══════════════════════════════════════════════════════════════════════════════

REQUIRED_RESOURCE_FIELDS = {
    'template',
    'output_file',
    'change_flag',
    'diff_compare',
    'fabric_types',
}

REQUIRED_PIPELINE_FIELDS = {
    'resource_name',
    'module',
    'state',
    'change_flag_guard',
}


REQUIRED_FABRIC_TYPE_FIELDS = {
    'namespace',
    'file_subdir',
}

# Pipeline fields that are known/valid (for typo detection)
KNOWN_PIPELINE_FIELDS = {
    'resource_name',
    'module',
    'state',
    'state_full_run',
    'full_run_strategy',
    'data_key_full_run',
    'change_flag_guard',
    'data_model_guard',
    'delete_mode_guard',
    'skip_if_child_fabric',
    'requires_switches',
    'fabric_param',
    'skip_diff',
    'deploy',
    'save',
    'tag',
}

class RegistryLoader:
    """
    Generic loader for YAML registry files under resources/.

    Provides:
      - Cached loading via lru_cache (loaded once per Ansible run)
      - Auto-discovery of collection path from __file__ location
      - Tag filtering for pipeline steps
      - Cross-reference, symmetry, and schema validation
    """

    @staticmethod
    @lru_cache(maxsize=None)
    def load(collection_path, registry_name):
        """
        Load a named YAML registry file from resources/.

        Args:
            collection_path: Root path of the collection (cisco/nac_dc_vxlan/)
            registry_name:   Name of the registry file (without .yml extension)

        Returns:
            Parsed YAML content as a dict.

        Raises:
            FileNotFoundError: If the registry file does not exist.
            yaml.YAMLError: If the file contains invalid YAML.

        Example:
            resource_types = RegistryLoader.load('/path/to/collection', 'resource_types')
        """
        registry_path = os.path.join(collection_path, 'resources', f'{registry_name}.yml')
        if not os.path.exists(registry_path):
            raise FileNotFoundError(
                f"Registry file not found: {registry_path}"
            )
        with open(registry_path, 'r') as f:
            data = yaml.safe_load(f)
        if data is None:
            return {}
        return data

    @staticmethod
    def get_collection_path():
        """
        Auto-derive the collection root from this file's location.

        This file lives at: plugins/plugin_utils/registry_loader.py
        Collection root is 3 directories up.

        Returns:
            Absolute path to the collection root directory.
        """
        # __file__ = plugins/plugin_utils/registry_loader.py
        # Go up: plugin_utils → plugins → collection_root
        this_dir = os.path.dirname(os.path.abspath(__file__))
        plugin_utils_dir = this_dir                             # plugins/plugin_utils/
        plugins_dir = os.path.dirname(plugin_utils_dir)         # plugins/
        collection_root = os.path.dirname(plugins_dir)          # collection root
        return collection_root

    @staticmethod
    def clear_cache():
        """Clear the LRU cache — useful in testing."""
        RegistryLoader.load.cache_clear()

    @staticmethod
    def filter_pipeline_by_tags(pipeline_steps, ansible_run_tags, role_tag=None):
        """
        Filter pipeline steps based on Ansible run tags.

        Filtering rules (applied in order):
          1. No active tags or empty → run all steps (no --tags specified)
          2. 'all' in active tags → run all steps (Ansible convention)
          3. role_tag in active tags → run all steps (role-level bypass)
          4. Otherwise → include only steps whose tag matches an active tag
          5. Steps with no tag field (tag is None) → always included

        Args:
            pipeline_steps: List of pipeline step dicts from YAML registry.
            ansible_run_tags: Set/list of tags from ansible_run_tags.
            role_tag: Optional role-level tag from registry. If present in
                      ansible_run_tags, bypasses per-step filtering.

        Returns:
            Filtered list of pipeline steps.
        """
        if not ansible_run_tags or 'all' in ansible_run_tags:
            return pipeline_steps

        if role_tag and role_tag in ansible_run_tags:
            return pipeline_steps

        filtered = []
        for step in pipeline_steps:
            step_tag = step.get('tag')
            if step_tag is None:
                # Infrastructure steps (no tag) always run
                filtered.append(step)
            elif isinstance(step_tag, list):
                # List tags — include if ANY tag matches (shared prep steps)
                if set(step_tag) & set(ansible_run_tags):
                    filtered.append(step)
            elif step_tag in ansible_run_tags:
                filtered.append(step)
        return filtered

    # ══════════════════════════════════════════════════════════════════════════
    # Validation Methods (#6 — Registry Validation)
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def validate_all(collection_path):
        """
        Run all three validation checks and return combined results.

        This is the primary entry point for registry validation. Call it
        at plugin startup (with -vvv) or as part of CI.

        Args:
            collection_path: Root path of the collection.

        Returns:
            dict with:
              - 'errors': List of error strings (things that will break)
              - 'warnings': List of warning strings (things that might be wrong)
              - 'valid': Boolean — True if no errors
        """
        errors = []
        warnings = []

        # Load all registries
        try:
            resource_types = RegistryLoader.load(collection_path, 'resource_types')
            fabric_types = RegistryLoader.load(collection_path, 'fabric_types')
            create_resources = RegistryLoader.load(collection_path, 'create_resources')
            remove_resources = RegistryLoader.load(collection_path, 'remove_resources')
        except (FileNotFoundError, yaml.YAMLError) as e:
            return {
                'errors': [f"Failed to load registries: {str(e)}"],
                'warnings': [],
                'valid': False,
            }

        # 1. Schema validation
        schema_errors = RegistryLoader.validate_schema(
            resource_types, create_resources, remove_resources, fabric_types,
        )
        errors.extend(schema_errors)

        # 2. Cross-reference validation
        xref_errors = RegistryLoader.validate_cross_references(
            resource_types, create_resources, remove_resources, fabric_types,
        )
        errors.extend(xref_errors)

        # 3. Pipeline symmetry validation
        symmetry_warnings = RegistryLoader.validate_pipeline_symmetry(
            create_resources, remove_resources
        )
        warnings.extend(symmetry_warnings)

        return {
            'errors': errors,
            'warnings': warnings,
            'valid': len(errors) == 0,
        }

    @staticmethod
    def validate_cross_references(resource_types, create_resources, remove_resources, fabric_types):
        """
        Verify that all cross-references between registry files are valid.

        Checks:
          - Pipeline step resource_name values exist in resource_types
            (internal methods starting with '_' and null are excluded)
          - Fabric type keys in pipelines exist in fabric_types
          - fabric_types lists in resource_types reference valid fabric type keys

        Args:
            resource_types:    Parsed resource_types.yml content
            create_resources:  Parsed create_resources.yml content
            remove_resources:  Parsed remove_resources.yml content
            fabric_types:      Parsed fabric_types.yml content

        Returns:
            List of error strings. Empty list means all references are valid.
        """
        errors = []

        valid_resources = set(resource_types.get('resource_types', {}).keys())
        valid_fabrics = set(fabric_types.get('fabric_types', {}).keys())

        # Validate create/remove pipeline references
        for pipeline_name, pipelines_data in [
            ('create', create_resources),
            ('remove', remove_resources),
        ]:
            pipeline_key = f'{pipeline_name}_resources'
            pipeline_dict = pipelines_data.get(pipeline_key, {})

            for fabric_type, steps in pipeline_dict.items():
                # Skip non-pipeline keys like 'role_tag'
                if fabric_type == 'role_tag':
                    continue

                # Validate fabric type reference
                if fabric_type not in valid_fabrics:
                    errors.append(
                        f"{pipeline_name} pipeline: unknown fabric_type '{fabric_type}'"
                    )

                if not isinstance(steps, list):
                    continue

                for idx, step in enumerate(steps):
                    resource_name = step.get('resource_name')
                    module = step.get('module', '')

                    # Skip internal methods and null resource names
                    if resource_name is None or (isinstance(module, str) and module.startswith('_')):
                        continue

                    if resource_name not in valid_resources:
                        errors.append(
                            f"{pipeline_name} pipeline [{fabric_type}] step {idx}: "
                            f"unknown resource_name '{resource_name}'"
                        )

        # Validate common pipeline references are no longer needed
        # (common role uses resource_types.yml directly via build_resource_data)

        # Validate resource fabric_types references
        for name, cfg in resource_types.get('resource_types', {}).items():
            for ft in cfg.get('fabric_types', []):
                if ft not in valid_fabrics:
                    errors.append(
                        f"resource_types '{name}': unknown fabric_type '{ft}'"
                    )

        return errors

    @staticmethod
    def validate_pipeline_symmetry(create_resources, remove_resources):
        """
        Verify create/remove pipeline step correspondence.

        For each fabric type, warns when:
          - A resource has a create step but no remove step
          - A resource has a remove step but no create step

        Internal methods (starting with '_') and null resource names are
        excluded from symmetry checks since orchestration-only steps don't
        require counterparts.

        Args:
            create_resources:  Parsed create_resources.yml content
            remove_resources:  Parsed remove_resources.yml content

        Returns:
            List of warning strings. Empty list means all steps are symmetric.
        """
        warnings = []

        create_dict = create_resources.get('create_resources', {})
        remove_dict = remove_resources.get('remove_resources', {})

        # Get all fabric types from both pipelines
        all_fabric_types = set()
        for ft in create_dict:
            if ft != 'role_tag':
                all_fabric_types.add(ft)
        for ft in remove_dict:
            if ft != 'role_tag':
                all_fabric_types.add(ft)

        for fabric_type in sorted(all_fabric_types):
            create_steps = create_dict.get(fabric_type, [])
            remove_steps = remove_dict.get(fabric_type, [])

            # Extract non-internal resource names
            create_resources = set()
            for step in (create_steps if isinstance(create_steps, list) else []):
                rn = step.get('resource_name')
                module = step.get('module', '')
                if rn is not None and not (isinstance(module, str) and module.startswith('_')):
                    create_resources.add(rn)

            remove_resources = set()
            for step in (remove_steps if isinstance(remove_steps, list) else []):
                rn = step.get('resource_name')
                module = step.get('module', '')
                if rn is not None and not (isinstance(module, str) and module.startswith('_')):
                    remove_resources.add(rn)

            create_only = create_resources - remove_resources
            remove_only = remove_resources - create_resources

            if create_only:
                warnings.append(
                    f"{fabric_type}: created but never removed: {sorted(create_only)}"
                )
            if remove_only:
                warnings.append(
                    f"{fabric_type}: removed but never created: {sorted(remove_only)}"
                )

        return warnings

    @staticmethod
    def validate_schema(resource_types, create_resources, remove_resources, fabric_types):
        """
        Validate that all registry entries have the required fields.

        Catches typos like 'chang_flag_guard' instead of 'change_flag_guard'
        at load time rather than at runtime when the missing value would
        silently be None.

        Args:
            resource_types:    Parsed resource_types.yml content
            create_resources:  Parsed create_resources.yml content
            remove_resources:  Parsed remove_resources.yml content
            fabric_types:      Parsed fabric_types.yml content

        Returns:
            List of error strings. Empty list means all schemas are valid.
        """
        errors = []

        # Validate resource_types entries
        for name, cfg in resource_types.get('resource_types', {}).items():
            if not isinstance(cfg, dict):
                errors.append(f"resource_types '{name}': entry is not a dict")
                continue
            missing = REQUIRED_RESOURCE_FIELDS - set(cfg.keys())
            if missing:
                errors.append(
                    f"resource_types '{name}': missing required fields: {sorted(missing)}"
                )

        # Validate fabric_types entries
        for name, cfg in fabric_types.get('fabric_types', {}).items():
            if not isinstance(cfg, dict):
                errors.append(f"fabric_types '{name}': entry is not a dict")
                continue
            missing = REQUIRED_FABRIC_TYPE_FIELDS - set(cfg.keys())
            if missing:
                errors.append(
                    f"fabric_types '{name}': missing required fields: {sorted(missing)}"
                )

        # Validate pipeline step entries
        for pipeline_name, pipelines_data in [
            ('create', create_resources),
            ('remove', remove_resources),
        ]:
            pipeline_key = f'{pipeline_name}_resources'
            pipeline_dict = pipelines_data.get(pipeline_key, {})

            for fabric_type, steps in pipeline_dict.items():
                if fabric_type == 'role_tag':
                    continue
                if not isinstance(steps, list):
                    errors.append(
                        f"{pipeline_name} pipeline '{fabric_type}': value is not a list"
                    )
                    continue

                for idx, step in enumerate(steps):
                    if not isinstance(step, dict):
                        errors.append(
                            f"{pipeline_name} pipeline [{fabric_type}] step {idx}: "
                            f"entry is not a dict"
                        )
                        continue

                    missing = REQUIRED_PIPELINE_FIELDS - set(step.keys())
                    if missing:
                        errors.append(
                            f"{pipeline_name} pipeline [{fabric_type}] step {idx} "
                            f"({step.get('resource_name', '?')}): "
                            f"missing required fields: {sorted(missing)}"
                        )

                    # Check for unknown fields (potential typos)
                    unknown = set(step.keys()) - KNOWN_PIPELINE_FIELDS
                    if unknown:
                        # This is a warning-level issue but reported as error
                        # to be conservative — unknown fields are likely typos
                        errors.append(
                            f"{pipeline_name} pipeline [{fabric_type}] step {idx} "
                            f"({step.get('resource_name', '?')}): "
                            f"unknown fields (possible typos): {sorted(unknown)}"
                        )

        return errors

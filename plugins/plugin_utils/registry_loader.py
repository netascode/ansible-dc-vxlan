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
import yaml
from functools import lru_cache

from ansible.utils.display import Display

display = Display()


class RegistryLoader:
    """
    Generic loader for YAML registry files under objects/.

    Provides a single entry point for all plugins to load their
    data-driven configuration from external YAML files located in
    the collection's objects/ directory.

    Usage:
        from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.registry_loader import RegistryLoader

        resource_types = RegistryLoader.load('/path/to/collection', 'resource_types')
        pipelines = RegistryLoader.load('/path/to/collection', 'create_pipelines')
    """

    @staticmethod
    @lru_cache(maxsize=None)
    def load(collection_path, registry_name):
        """
        Load a named YAML registry file.

        Args:
            collection_path: Root path of the cisco.nac_dc_vxlan collection.
            registry_name:   Name of the registry file (without .yml extension).

        Returns:
            Parsed YAML content as a dict.

        Raises:
            FileNotFoundError: If the registry file does not exist.
            yaml.YAMLError: If the registry file contains invalid YAML.
        """
        registry_path = os.path.join(collection_path, 'objects', f'{registry_name}.yml')

        if not os.path.exists(registry_path):
            raise FileNotFoundError(
                f"Registry file not found: {registry_path}. "
                f"Expected at: <collection_root>/objects/{registry_name}.yml"
            )

        display.v(f"RegistryLoader: Loading registry '{registry_name}' from {registry_path}")

        with open(registry_path, 'r') as f:
            data = yaml.safe_load(f)

        if data is None:
            display.warning(f"RegistryLoader: Registry file '{registry_name}' is empty, returning empty dict")
            return {}

        return data

    @staticmethod
    def get_collection_path():
        """
        Derive the collection root path from this file's location.

        This file lives at:
            <collection_root>/plugins/plugin_utils/registry_loader.py

        So the collection root is three directories up.

        Returns:
            Absolute path to the collection root directory.
        """
        this_file = os.path.abspath(__file__)
        # plugins/plugin_utils/registry_loader.py → plugins/plugin_utils → plugins → collection_root
        collection_path = os.path.dirname(os.path.dirname(os.path.dirname(this_file)))
        return collection_path

    @staticmethod
    def filter_pipeline_by_tags(pipeline, active_tags, role_tag=None):
        """
        Filter pipeline steps based on active Ansible run tags.

        Implements per-step tag selectivity within a consolidated action
        plugin, preserving the tag-based selective execution that operators
        relied on with the original per-task YAML approach.

        Filtering rules (applied in order):
        1. No active tags or empty → run all steps (no --tags specified)
        2. 'all' in active tags → run all steps (Ansible convention)
        3. role_tag in active tags → run all steps (role-level tag = entire role)
        4. Otherwise → include only steps whose tag matches an active tag
        5. Steps with no tag field (tag is None) → always included

        Args:
            pipeline:    List of pipeline step dicts from YAML registry.
            active_tags: List of active Ansible tags (from ansible_run_tags).
            role_tag:    The role-level bypass tag (e.g., 'role_create')
                         from the pipeline registry's role_tag field.
                         When present in active_tags, all steps run.

        Returns:
            Filtered list of pipeline steps.
        """
        # Rules 1-2: No filtering when no tags specified or 'all' is active
        if not active_tags or 'all' in active_tags:
            return pipeline

        # Rule 3: Role-level bypass — run full pipeline
        if role_tag and role_tag in active_tags:
            return pipeline

        # Rules 4-5: Per-step tag filtering
        return [
            step for step in pipeline
            if step.get('tag') is None or step.get('tag') in active_tags
        ]

    @staticmethod
    def clear_cache():
        """
        Clear the LRU cache for all loaded registries.

        Useful in testing or when registry files have been modified
        during a single Ansible run.
        """
        RegistryLoader.load.cache_clear()

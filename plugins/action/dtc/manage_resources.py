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
Manage Resources — Consolidated creation pipeline for all fabric types.

Replaces the dtc/create role's per-fabric-type sub_main_*.yml files and
task files (~18 files, ~900 lines YAML) with a single data-driven plugin.

Pipeline definitions are loaded from objects/create_resources.yml.

Extends PipelineRunnerBase with create-specific behavior:
  - _resolve_step_data: diff.updated preference (Recommendation #7)
  - skip_diff: Pipeline field to bypass diff narrowing (e.g. vpc_fabric_peering_links)

Shared infrastructure (module execution, pipeline skeleton, tag filtering,
change flag guards, multisite methods, config-save) lives in plugin_utils/.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.utils.display import Display

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.pipeline_base import (
    PipelineRunnerBase,
)
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.dtc_action_base import (
    DtcPipelineActionBase,
)

display = Display()


class ResourceManager(PipelineRunnerBase):
    """
    Create pipeline runner.

    Extends PipelineRunnerBase with create-specific data resolution
    (diff.updated preference) and skip_diff support.
    """

    REGISTRY_KEY = 'create_resources'
    OPERATION = 'create'

    def __init__(self, params, executor, task_vars):
        super().__init__(params, executor, task_vars)
        self.nd_version = params.get('nd_version', '')

    # ══════════════════════════════════════════════════════════════════════════
    # Data Resolution (create-specific)
    # ══════════════════════════════════════════════════════════════════════════

    def _resolve_step_data(self, resource_name, step):
        """
        Resolve the data and state to send for a create step.

        Recommendation #7: Uses explicit run_map_diff_run parameter to
        gate the diff.updated preference instead of relying on cleanup cascade.

        When diff_run is active and force_run_all is False:
          - Prefers diff.updated (narrowed data set for changed items only)
          - Falls back to full data if diff.updated is not available
        When diff_run is disabled or force_run_all is True:
          - Always uses full data (complete reconciliation)

        Args:
            resource_name: Logical name of the resource.
            step: Pipeline step dict.

        Returns:
            Tuple of (data_list, state_string).
        """
        state = step.get('state')
        skip_diff = step.get('skip_diff', False)
        data = self._resolve_create_data(resource_name, skip_diff=skip_diff)
        return (data, state)

    def _resolve_create_data(self, resource_name, skip_diff=False):
        """
        Resolve the data to send for a create step.

        Args:
            resource_name: Logical name of the resource.
            skip_diff: If True, always use raw data (bypass diff narrowing).

        Returns:
            Data list, or None/empty list if no data.
        """
        resource_entry = self.resource_data.get(resource_name, {})

        if not isinstance(resource_entry, dict):
            return resource_entry if resource_entry else []

        # module_data is the authoritative data source set by build_resource_data.
        # For most resources this equals the raw template data. For resources with
        # post-hooks (e.g. inventory/get_credentials), this is the hook-transformed
        # data ready for the NDFC module.
        data = resource_entry.get('module_data', resource_entry.get('data', []))

        # Recommendation #7: Only use diff.updated when diff_run is explicitly active
        # skip_diff bypasses this for resources that must always send full data
        # (e.g. vpc_fabric_peering_links)
        if not skip_diff and self.run_map_diff_run and not self.force_run_all:
            diff = resource_entry.get('diff')
            if diff and isinstance(diff, dict):
                diff_data = diff.get('updated')
                if diff_data is not None:
                    data = diff_data

        return data


class ActionModule(DtcPipelineActionBase):
    """
    Ansible ActionBase wrapper for manage_resources.

    Delegates to ResourceManager via the DtcPipelineActionBase framework.
    """

    OPERATION_LABEL = 'Manage resources'

    def _create_runner(self, params, executor, task_vars):
        return ResourceManager(params, executor, task_vars)

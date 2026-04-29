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

Pipeline definitions are loaded from resources/create_resources.yml.

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

    # ══════════════════════════════════════════════════════════════════════════
    # Create-Specific Internal Methods
    # ══════════════════════════════════════════════════════════════════════════

    def _fabric_links_query_and_filter(self, resource_name, step):
        """
        Query NDFC for existing fabric links and filter via existing_links_check.

        Replicates the pre-processing from roles/dtc/create/tasks/common/links.yml:
          1. Resolve fabric_links data (respecting diff_run)
          2. Query existing links from NDFC (dcnm_links state: query)
          3. Run existing_links_check action plugin to filter/transform
          4. Update self.resource_data['fabric_links'] with filtered result

        The subsequent dcnm_links step picks up the filtered data via
        _resolve_step_data naturally.
        """
        # Step 1: Resolve the fabric_links data (respecting diff_run)
        data, _ = self._resolve_step_data(resource_name, step)
        if not data:
            return {'changed': False, 'msg': 'No fabric links data to filter'}

        # Step 2: Query existing links from NDFC
        query_result = self.executor.execute(
            module_name="cisco.dcnm.dcnm_links",
            state="query",
            config=[{"dst_fabric": self.fabric_name}],
            fabric_name=self.fabric_name,
            fabric_param="src_fabric",
        )

        existing_links = query_result.get('response', [])
        if not existing_links:
            # No existing links — all configured links are new/required
            return {'changed': False, 'msg': 'No existing links on controller'}

        # Step 3: Filter via existing_links_check action plugin
        switches = (
            self.data_model.get('vxlan', {})
            .get('topology', {})
            .get('switches', [])
        )

        filter_result = self.executor.execute_plugin(
            module_name="cisco.nac_dc_vxlan.dtc.existing_links_check",
            module_args={
                "existing_links": existing_links,
                "fabric_links": data,
                "switch_data_model": switches,
            },
        )

        if filter_result.get('failed'):
            return {
                'failed': True,
                'msg': (
                    f"existing_links_check failed: "
                    f"{filter_result.get('msg', 'unknown error')}"
                ),
            }

        # Step 4: Update resource_data so the next step picks up filtered links
        required_links = filter_result.get('required_links', [])

        resource_entry = self.resource_data.get('fabric_links', {})
        if isinstance(resource_entry, dict):
            resource_entry['module_data'] = required_links
        else:
            self.resource_data['fabric_links'] = {'module_data': required_links}

        display.v(
            f"CREATE [{self.fabric_name}] fabric_links: "
            f"{len(data)} configured → {len(required_links)} after filter"
        )

        return {'changed': False}
      
    def _underlay_ip_remote_diff(self, resource_name, step):
        """
        Remote diff: reconcile underlay IP data model against controller state.

        This method implements Phase 2 of the two-phase comparison:

        Phase 1 - Local YAML Comparison (handled by common/files):
            Compares the previous and current rendered YAML
            (ndfc_underlay_ip_address.yml) to detect local data model changes.
            Output: diff.updated entries for changed resources.

            Example: user changes loopback0 ipv4 from 10.1.0.1/32
            to 10.1.0.2/32 in the data model -> Phase 1 detects the diff.

        Phase 2 - Controller Reconciliation (this method):
            Queries the controller (ND) pool resources via
            underlay_ip_manual_allocation_filter and compares against the desired config.
            Reduces module_data to only entries needing controller updates.

            Example: 5 switches in data model, but 2 already have the
            correct pool allocation on the controller -> filtered_config
            returns only the 3 that need updates.

        In diff_run mode the local YAML diff (Phase 1) already narrows scope,
        so Phase 2 is skipped to avoid redundant controller queries.

        Args:
            resource_name: Resource identifier (e.g. underlay_ip_address).
            step: Pipeline step dict from create_resources.yml.

        Returns:
            dict with changed and optionally failed/msg keys.
        """
        data, _ = self._resolve_step_data(resource_name, step)
        if not data:
            return {"changed": False, "msg": "No underlay_ip_address data to audit"}

        if self.run_map_diff_run:
            return {
                "changed": False,
                "msg": "Diff run active; skipping underlay IP audit",
            }

        scope_filter = self.task_vars.get("underlay_ip_audit_scope_filter", "all")

        module_args = {
            "fabric": self.fabric_name,
            "desired_config": data,
            "scope_filter": scope_filter,
        }
        if "underlay_ip_audit_pools" in self.task_vars:
            module_args["query_pools"] = self.task_vars["underlay_ip_audit_pools"]

        audit_result = self.executor.execute_plugin(
            module_name="cisco.nac_dc_vxlan.dtc.underlay_ip_manual_allocation_filter",
            module_args=module_args,
        )

        if audit_result.get("failed"):
            return {
                "failed": True,
                "msg": audit_result.get(
                    "msg", "underlay_ip_manual_allocation_filter failed"
                ),
            }

        filtered_config = audit_result.get("filtered_config", [])
        resource_entry = self.resource_data.get(resource_name, {})
        if isinstance(resource_entry, dict):
            resource_entry["module_data"] = filtered_config
        else:
            self.resource_data[resource_name] = {
                "module_data": filtered_config,
            }

        display.v(
            f"CREATE [{self.fabric_name}] underlay_ip_address: "
            f"{len(data)} configured → {len(filtered_config)} after audit"
        )
        if display.verbosity >= 2:
            matched = audit_result.get("matched_total", 0)
            display.vv(
                f"CREATE [{self.fabric_name}] underlay_ip_address: "
                f"{matched} matched controller, {len(filtered_config)} need update"
            )
        if display.verbosity >= 3:
            for entry in audit_result.get("missing_or_mismatch", []):
                display.vvv(
                    f"  [{self.fabric_name}] {entry.get('reason')}: "
                    f"entity={entry.get('entity')} expected={entry.get('expected')} "
                    f"actual={entry.get('actual')}"
                )
        return {"changed": False}

class ActionModule(DtcPipelineActionBase):
    """
    Ansible ActionBase wrapper for manage_resources.

    Delegates to ResourceManager via the DtcPipelineActionBase framework.
    """

    OPERATION_LABEL = 'Manage resources'

    def _create_runner(self, params, executor, task_vars):
        return ResourceManager(params, executor, task_vars)

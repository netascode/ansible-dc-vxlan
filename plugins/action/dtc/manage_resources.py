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

import json

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

   def _policy_remote_diff(self, resource_name, step):
        """
        Two-phase policy diff: reduce policies sent to dcnm_policy module.

        Phase 1 - Local YAML Comparison (diff_run=true):
            Compares previous and current rendered ndfc_policy.yml.
            Only policies that changed locally are forwarded.

            Example: user adds nac_ntp to leaf-201 -> only leaf-201
            switch block is sent to dcnm_policy.

        Phase 2 - Controller Reconciliation (diff_run=false):
            Queries NDFC pagination API for all nac_ policies in the
            fabric and compares against desired rendered config.

            Example: 200 total policies, 180 match controller
            -> only 20 sent to dcnm_policy.

        Comparison key: (switch_ip, policy_description)
        Compared fields: template name, priority, policy_vars vs nvPairs

        Args:
            resource_name: Resource identifier (policy).
            step: Pipeline step dict from create_resources.yml.

        Returns:
            dict with changed and optionally failed/msg keys.
        """
        data, _ = self._resolve_step_data(resource_name, step)
        if not data:
            return {'changed': False, 'msg': 'No policy data to filter'}

        if self.run_map_diff_run:
            # Phase 1 handled by diff_compare in build phase.
            # _resolve_step_data already narrowed to diff.updated.
            # No controller query needed — skip.
            return {'changed': False, 'status': 'skipped', 'reason': 'local diff handled by diff_compare'}

        return self._policy_controller_diff(resource_name, data)

    def _policy_controller_diff(self, resource_name, desired_config):
        """
        Phase 2: Compare desired policies against NDFC controller state.

        Queries the pagination API for all policies in the fabric, filters
        to nac_ managed policies, and compares against desired config.

        API: GET /appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/
             policies/pagination?fabricName={fabricName}

        Comparison:
            Key: (switch_ip, description)
            Fields: template name (name vs templateName),
                    priority, policy_vars vs nvPairs

        nvPairs internal keys excluded from comparison (auto-managed by NDFC):
            FABRIC_NAME, POLICY_ID, POLICY_DESC, SECENTITY, SECENTTYPE

        Args:
            resource_name: Resource identifier (policy).
            desired_config: Current rendered policy config.

        Returns:
            dict with changed and optionally failed/msg keys.
        """
        api_path = (
            "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/policies/"
            f"pagination?fabricName={self.fabric_name}"
        )

        query_result = self.executor.execute_rest("GET", api_path)

        if query_result.get('failed'):
            display.warning(
                f"Policy pagination query failed: "
                f"{query_result.get('msg', 'unknown')}. Keeping all policies."
            )
            return {'changed': False}

        # Parse controller response
        response_data = query_result.get('response', {})
        if isinstance(response_data, str):
            try:
                response_data = json.loads(response_data)
            except (json.JSONDecodeError, TypeError):
                display.warning("Failed to parse policy pagination response")
                return {'changed': False}

        if isinstance(response_data, dict):
            controller_policies = response_data.get('DATA', [])
        elif isinstance(response_data, list):
            controller_policies = response_data
        else:
            controller_policies = []

        # Build lookup: {(ipAddress, description): controller_policy}
        # Only nac_ managed policies with empty source (user-created)
        ctrl_lookup = {}
        for cpol in controller_policies:
            desc = cpol.get('description', '')
            if (desc.startswith('nac_') or desc.startswith('nace_')) and cpol.get('source', '') == '':
                ip = cpol.get('ipAddress', '')
                ctrl_lookup[(ip, desc)] = cpol

        # Filter desired config to new or changed policies only
        filtered_config = []
        total_policies = 0
        diff_policies = 0

        for switch_block in desired_config:
            filtered_switches = []
            for sw in switch_block.get('switch', []):
                ip = sw.get('ip', '')
                diff_pols = []
                for pol in sw.get('policies', []):
                    total_policies += 1
                    desc = pol.get('description', '')
                    ctrl_pol = ctrl_lookup.get((ip, desc))

                    if ctrl_pol is None or self._policy_differs_from_controller(pol, ctrl_pol):
                        diff_pols.append(pol)
                        diff_policies += 1

                if diff_pols:
                    filtered_switches.append({
                        'ip': ip,
                        'policies': diff_pols,
                    })

            if filtered_switches:
                filtered_config.append({'switch': filtered_switches})

        self._update_policy_resource_data(resource_name, filtered_config)

        display.v(
            f"CREATE [{self.fabric_name}] policy controller diff: "
            f"{total_policies} desired, {len(ctrl_lookup)} on controller "
            f"-> {diff_policies} to push"
        )
        return {'changed': False}

    def _policy_differs_from_controller(self, desired, controller):
        """
        Compare desired policy against controller policy from API.

        Field mapping:
            desired.name         <-> controller.templateName
            desired.priority     <-> controller.priority
            desired.policy_vars  <-> controller.nvPairs (filtered)

        nvPairs auto-managed keys excluded:
            FABRIC_NAME, POLICY_ID, POLICY_DESC, SECENTITY, SECENTTYPE

        Returns True if desired state differs from controller.
        """
        desc = desired.get('description', '?')

        if desired.get('name') != controller.get('templateName'):
            display.vvv(
                f"POLICY DIFF [{desc}]: template name "
                f"desired={desired.get('name')} vs ctrl={controller.get('templateName')}"
            )
            return True

        desired_priority = desired.get('priority')
        ctrl_priority = controller.get('priority')
        if desired_priority is not None and ctrl_priority is not None:
            if int(desired_priority) != int(ctrl_priority):
                display.vvv(
                    f"POLICY DIFF [{desc}]: priority "
                    f"desired={desired_priority} vs ctrl={ctrl_priority}"
                )
                return True

        desired_vars = desired.get('policy_vars') or {}
        ctrl_nv = controller.get('nvPairs', {})

        ndfc_internal_keys = {
            'FABRIC_NAME', 'POLICY_ID', 'POLICY_DESC',
            'SECENTITY', 'SECENTTYPE', 'PRIORITY',
        }

        # Desired vars must match controller
        for key, val in desired_vars.items():
            ctrl_val = ctrl_nv.get(key)
            if ctrl_val is None or str(val).strip() != str(ctrl_val).strip():
                display.vvv(
                    f"POLICY DIFF [{desc}]: var {key} "
                    f"desired={repr(str(val).strip()[:80])} vs "
                    f"ctrl={repr(str(ctrl_val).strip()[:80] if ctrl_val is not None else None)}"
                )
                return True

        return False

    def _update_policy_resource_data(self, resource_name, filtered_config):
        """Update resource_data with filtered policy config."""
        resource_entry = self.resource_data.get(resource_name, {})
        if isinstance(resource_entry, dict):
            resource_entry['module_data'] = filtered_config
        else:
            self.resource_data[resource_name] = {
                'module_data': filtered_config,
            }

class ActionModule(DtcPipelineActionBase):
    """
    Ansible ActionBase wrapper for manage_resources.

    Delegates to ResourceManager via the DtcPipelineActionBase framework.
    """

    OPERATION_LABEL = 'Manage resources'

    def _create_runner(self, params, executor, task_vars):
        return ResourceManager(params, executor, task_vars)

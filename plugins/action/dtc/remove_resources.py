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
Remove Resources — Consolidated removal pipeline for all fabric types.

Replaces the dtc/remove role's per-fabric-type sub_main_*.yml files and
task files (~16 files, ~800 lines YAML) with a single data-driven plugin.

Pipeline definitions are loaded from resources/remove_resources.yml.

Extends PipelineRunnerBase with remove-specific behavior:
  - Recommendation #2: delete_mode_guard safety flags per step
  - Recommendation #4: Correct vPC peers module (dcnm_vpc_pair with src_fabric)
  - state_full_run: Dual-state removal (deleted for diff_run, overridden for full)
  - skip_if_child_fabric: Guard for VRFs/networks on active MSD child fabrics
  - requires_switches: Guard for steps that need switches in the fabric

Shared infrastructure (module execution, pipeline skeleton, tag filtering,
change flag guards, multisite methods) lives in plugin_utils/.
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


class ResourceRemover(PipelineRunnerBase):
    """
    Remove pipeline runner.

    Extends PipelineRunnerBase with remove-specific data resolution
    (diff.removed with dual-state), additional guards (delete_mode,
    child_fabric, requires_switches), and controller query helpers.
    """

    REGISTRY_KEY = 'remove_resources'
    OPERATION = 'remove'

    def __init__(self, params, executor, task_vars):
        super().__init__(params, executor, task_vars)
        self.stage_remove = params.get('stage_remove', False)

        # Recommendation #2: delete_mode_guard support
        # Read delete mode flags from task_vars (user-configurable via group_vars/host_vars)
        self.delete_modes = {
            'interface_delete_mode': task_vars.get('interface_delete_mode', False),
            'vrf_delete_mode': task_vars.get('vrf_delete_mode', False),
            'network_delete_mode': task_vars.get('network_delete_mode', False),
            'vpc_delete_mode': task_vars.get('vpc_delete_mode', False),
            'inventory_delete_mode': task_vars.get('inventory_delete_mode', False),
            'edge_connections_delete_mode': task_vars.get('edge_connections_delete_mode', False),
            'policy_delete_mode': task_vars.get('policy_delete_mode', False),
            'tor_pairing_delete_mode': task_vars.get('tor_pairing_delete_mode', False),
        }

    # ══════════════════════════════════════════════════════════════════════════
    # Pipeline Hooks (remove-specific overrides)
    # ══════════════════════════════════════════════════════════════════════════

    def _pre_pipeline_setup(self):
        """Pre-fetch fabric switch list for guards and internal methods."""
        self.fabric_switch_list = self._get_fabric_switches()
        return {'switch_list': self.fabric_switch_list}

    def _check_additional_guards(self, step, context):
        """
        Remove-specific guards: delete_mode, child_fabric, requires_switches.

        Checked before the shared change_flag_guard in the base class.
        """
        resource_name = step['resource_name']
        module = step['module']

        # ── Guard 1: delete_mode_guard (Recommendation #2) ────────────
        if not self._check_delete_mode(step):
            display.v(
                f"REMOVE [{self.fabric_name}] Skipping {resource_name}: "
                f"delete_mode_guard '{step.get('delete_mode_guard')}' is disabled"
            )
            return {
                'resource_name': resource_name,
                'module': module,
                'status': 'skipped',
                'reason': (
                    f"delete_mode_guard '{step.get('delete_mode_guard')}' "
                    f"is disabled"
                ),
            }

        # ── Guard 2: skip_if_child_fabric ─────────────────────────────
        if step.get('skip_if_child_fabric') and self._is_active_child_fabric():
            display.v(
                f"REMOVE [{self.fabric_name}] Skipping {resource_name}: "
                f"fabric is an active MSD child"
            )
            return {
                'resource_name': resource_name,
                'module': module,
                'status': 'skipped',
                'reason': 'active child fabric — skipping to prevent MSD conflict',
            }

        # ── Guard 3: requires_switches ────────────────────────────────
        if step.get('requires_switches') and not context.get('switch_list'):
            return {
                'resource_name': resource_name,
                'module': module,
                'status': 'skipped',
                'reason': 'no switches in fabric',
            }

        return None  # All guards passed

    # ══════════════════════════════════════════════════════════════════════════
    # Data Resolution (remove-specific)
    # ══════════════════════════════════════════════════════════════════════════

    def _resolve_step_data(self, resource_name, step):
        """
        Determine the data set and module state for resource removal.

        When diff_run is active and force_run_all is False:
          - Uses diff.removed list with the default 'state' (typically 'deleted')
        When diff_run is disabled or force_run_all is True:
          - Uses full resource data with 'state_full_run' if declared (typically 'overridden')
          - Falls back to 'state' if 'state_full_run' is not declared

        Args:
            resource_name: Logical name of the resource.
            step: Pipeline step dict from remove_resources.yml.

        Returns:
            Tuple of (data_list, resolved_state_string).
        """
        resource_entry = self.resource_data.get(resource_name, {})
        default_state = step.get('state')
        full_run_state = step.get('state_full_run')
        data_key_full_run = step.get('data_key_full_run', 'data')

        if not isinstance(resource_entry, dict):
            return (resource_entry if resource_entry else [], default_state)

        # Diff-based run: use diff.removed with default state (deleted)
        if self.run_map_diff_run and not self.force_run_all:
            diff = resource_entry.get('diff')
            if diff and isinstance(diff, dict):
                removed = diff.get('removed', [])
                if removed:
                    return (removed, default_state)
            return ([], default_state)

        # Full run: use full data with full_run_state if declared, else default
        resolved_state = full_run_state if full_run_state else default_state
        data = resource_entry.get(data_key_full_run, [])
        return (data, resolved_state)

    # ══════════════════════════════════════════════════════════════════════════
    # Remove-Specific Guard Helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _check_delete_mode(self, step):
        """
        Check if the user-configurable delete mode flag allows this step.

        Recommendation #2: Each pipeline step can declare a delete_mode_guard
        field. If present, the corresponding user variable must be truthy
        for the step to execute. If absent, the step always executes.

        Args:
            step: Pipeline step dict.

        Returns:
            True if the step should execute, False if it should be skipped.
        """
        delete_mode_flag = step.get('delete_mode_guard')
        if not delete_mode_flag:
            return True  # No guard configured — always execute
        return bool(self.delete_modes.get(delete_mode_flag, False))

    def _is_active_child_fabric(self):
        """
        Check if the current fabric is an active child in an MSD deployment.

        Caches the result as an instance variable after the first API call,
        since multiple pipeline steps may check this within a single execution.

        Returns:
            True if the fabric is an active MSD child, False otherwise.
        """
        if hasattr(self, '_cached_child_fabric_result'):
            return self._cached_child_fabric_result

        # If centralized controller discovery has already set this fact,
        # use it directly from task_vars
        if 'is_active_child_fabric' in self.task_vars:
            self._cached_child_fabric_result = bool(
                self.task_vars['is_active_child_fabric']
            )
            return self._cached_child_fabric_result

        # Fall back to querying the controller
        result = self.executor.execute_rest(
            "GET",
            "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control"
            "/fabrics/msd/fabric-associations",
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

        self._cached_child_fabric_result = is_child
        return is_child

    def _get_fabric_switches(self):
        """
        Get the list of switches in the current fabric from NDFC.

        If centralized controller discovery has set the fabric_switches fact,
        uses that directly. Otherwise queries the controller.

        Returns:
            List of switch dicts, or empty list if no switches.
        """
        # Use centralized fact if available (Recommendation #3)
        if 'fabric_switches' in self.task_vars:
            switches = self.task_vars['fabric_switches']
            return switches if isinstance(switches, list) else []

        # Fall back to querying the controller
        result = self.executor.execute_rest(
            "GET",
            f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control"
            f"/fabrics/{self.fabric_name}/inventory/switchesByFabric",
        )

        try:
            data = result.get('response', {}).get('DATA', [])
            return data if isinstance(data, list) else []
        except (KeyError, TypeError):
            return []

    # ══════════════════════════════════════════════════════════════════════════
    # Remove-Specific Internal Methods
    # ══════════════════════════════════════════════════════════════════════════


class ActionModule(DtcPipelineActionBase):
    """
    Ansible ActionBase wrapper for remove_resources.

    Delegates to ResourceRemover via the DtcPipelineActionBase framework.
    """

    OPERATION_LABEL = 'Remove resources'

    def _create_runner(self, params, executor, task_vars):
        return ResourceRemover(params, executor, task_vars)

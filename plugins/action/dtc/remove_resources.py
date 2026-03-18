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
Remove Resources — Consolidated removal pipeline for all fabric types.

Replaces the dtc/remove role's per-fabric-type sub_main_*.yml files and
task files (~16 files, ~800 lines YAML) with a single data-driven plugin.

Pipeline definitions are loaded from objects/remove_pipelines.yml.

Implements:
  - Recommendation #2: delete_mode_guard safety flags per step
  - Recommendation #4: Correct vPC peers module (dcnm_vpc_pair with src_fabric)
  - state_full_run: Dual-state removal (deleted for diff_run, overridden for full)
  - skip_if_child_fabric: Guard for VRFs/networks on active MSD child fabrics
  - fabric_param: Configurable fabric parameter name per step
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.registry_loader import (
    RegistryLoader,
)

display = Display()


class ResourceRemover:
    """
    Core removal pipeline logic.

    Iterates through the remove pipeline for the given fabric type,
    checking guards (change_flag, delete_mode, child_fabric) and
    resolving the correct data set and module state based on the
    diff_run flag before calling NDFC modules.
    """

    def __init__(self, params, action_module, task_vars, tmp=None):
        """
        Initialize the resource remover.

        Args:
            params: Dict of task args from the role task YAML.
            action_module: Reference to the ActionModule instance for _execute_module.
            task_vars: Ansible task variables.
            tmp: Temporary directory (Ansible internal).
        """
        self.fabric_type = params['fabric_type']
        self.fabric_name = params['fabric_name']
        self.data_model = params['data_model']
        self.resource_data = params['resource_data']
        self.change_flags = params['change_flags']
        self.run_map_diff_run = params.get('run_map_diff_run', True)
        self.force_run_all = params.get('force_run_all', False)
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
        }

        self.action_module = action_module
        self.task_vars = task_vars
        self.tmp = tmp

        # Load pipeline from registry
        collection_path = RegistryLoader.get_collection_path()
        registry = RegistryLoader.load(collection_path, 'remove_pipelines')
        self.pipelines = registry.get('remove_pipelines', {})

    def remove(self):
        """
        Execute the ordered removal pipeline for the current fabric type.

        Returns:
            dict with:
              - 'results': List of per-step result dicts
              - 'failed': Boolean — True if any step failed
              - 'msg': Summary message
        """
        pipeline = self.pipelines.get(self.fabric_type)
        if pipeline is None:
            return {
                'results': [],
                'failed': True,
                'msg': f"No remove pipeline defined for fabric type: {self.fabric_type}",
            }

        # Filter by tags if needed
        ansible_run_tags = self.task_vars.get('ansible_run_tags', [])
        pipeline = RegistryLoader.filter_pipeline_by_tags(pipeline, ansible_run_tags)

        # Pre-fetch fabric switch list (used by requires_switches guard)
        switch_list = self._get_fabric_switches()

        step_results = []

        for step in pipeline:
            resource_name = step['resource_name']
            module = step['module']
            flag_name = step.get('change_flag_guard')

            # ── Guard 1: delete_mode_guard (Recommendation #2) ────────────
            if not self._check_delete_mode(step):
                step_results.append({
                    'resource_name': resource_name,
                    'module': module,
                    'status': 'skipped',
                    'reason': (
                        f"delete_mode_guard '{step.get('delete_mode_guard')}' "
                        f"is disabled"
                    ),
                })
                display.v(
                    f"REMOVE [{self.fabric_name}] Skipping {resource_name}: "
                    f"delete_mode_guard '{step.get('delete_mode_guard')}' is disabled"
                )
                continue

            # ── Guard 2: skip_if_child_fabric ─────────────────────────────
            if step.get('skip_if_child_fabric') and self._is_active_child_fabric():
                step_results.append({
                    'resource_name': resource_name,
                    'module': module,
                    'status': 'skipped',
                    'reason': 'active child fabric — skipping to prevent MSD conflict',
                })
                display.v(
                    f"REMOVE [{self.fabric_name}] Skipping {resource_name}: "
                    f"fabric is an active MSD child"
                )
                continue

            # ── Guard 3: change_flag_guard ────────────────────────────────
            if flag_name and not self.change_flags.get(flag_name, False):
                step_results.append({
                    'resource_name': resource_name,
                    'module': module,
                    'status': 'skipped',
                    'reason': f"change flag '{flag_name}' is False",
                })
                continue

            # ── Guard 4: requires_switches ────────────────────────────────
            if step.get('requires_switches') and not switch_list:
                step_results.append({
                    'resource_name': resource_name,
                    'module': module,
                    'status': 'skipped',
                    'reason': 'no switches in fabric',
                })
                continue

            # ── Internal method dispatch ──────────────────────────────────
            if isinstance(module, str) and module.startswith('_'):
                try:
                    method = getattr(self, module)
                    result = method(resource_name, step)
                    step_results.append({
                        'resource_name': resource_name,
                        'module': module,
                        'status': 'ok',
                        'result': result,
                    })
                except AttributeError:
                    step_results.append({
                        'resource_name': resource_name,
                        'module': module,
                        'status': 'failed',
                        'reason': f"Internal method '{module}' not found on ResourceRemover",
                    })
                    return {
                        'results': step_results,
                        'failed': True,
                        'msg': f"Internal method '{module}' not found",
                    }
                continue

            # ── Resolve data and state based on diff_run ──────────────────
            data, resolved_state = self._get_removal_data(resource_name, step)

            if not data:
                step_results.append({
                    'resource_name': resource_name,
                    'module': module,
                    'status': 'skipped',
                    'reason': 'no removal data',
                })
                continue

            # ── Determine fabric parameter name (#4 — vPC fix) ────────────
            module_config = step.get('module_config', {})
            fabric_param = module_config.get('fabric_param', 'fabric')

            # ── Execute NDFC module ───────────────────────────────────────
            deploy = step.get('deploy')

            display.v(
                f"REMOVE [{self.fabric_name}] Executing {module} for "
                f"{resource_name} with state={resolved_state}, "
                f"fabric_param={fabric_param}, items={len(data) if isinstance(data, list) else '?'}"
            )

            result = self._execute_ndfc_module(
                module_name=f"cisco.dcnm.{module}",
                state=resolved_state,
                config=data,
                deploy=deploy,
                fabric_param=fabric_param,
            )

            if result.get('failed'):
                step_results.append({
                    'resource_name': resource_name,
                    'module': module,
                    'status': 'failed',
                    'result': result,
                })
                return {
                    'results': step_results,
                    'failed': True,
                    'msg': (
                        f"Remove pipeline failed at step '{resource_name}' "
                        f"({module}): {result.get('msg', 'unknown error')}"
                    ),
                }

            step_results.append({
                'resource_name': resource_name,
                'module': module,
                'status': 'ok',
                'changed': result.get('changed', False),
                'result': result,
            })

        return {
            'results': step_results,
            'failed': False,
            'msg': f"Remove pipeline completed for {self.fabric_type} fabric '{self.fabric_name}'",
        }

    def _get_removal_data(self, resource_name, step):
        """
        Determine the data set and module state for resource removal.

        When diff_run is active and force_run_all is False:
          - Uses diff.removed list with the default 'state' (typically 'deleted')
        When diff_run is disabled or force_run_all is True:
          - Uses full resource data with 'state_full_run' if declared (typically 'overridden')
          - Falls back to 'state' if 'state_full_run' is not declared

        Args:
            resource_name: Logical name of the resource.
            step: Pipeline step dict from remove_pipelines.yml.

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
        result = self.action_module._execute_module(
            module_name="cisco.dcnm.dcnm_rest",
            module_args={
                "method": "GET",
                "path": (
                    f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control"
                    f"/fabrics/{self.fabric_name}/inventory/switchesByFabric"
                ),
            },
            task_vars=self.task_vars,
            tmp=self.tmp,
        )

        try:
            data = result.get('response', {}).get('DATA', [])
            return data if isinstance(data, list) else []
        except (KeyError, TypeError):
            return []

    # Modules with companion action plugins that must be invoked to replicate
    # native Ansible task execution (e.g. fabric discovery, metadata injection).
    MODULES_WITH_ACTION_PLUGINS = frozenset({
        'cisco.dcnm.dcnm_vrf',
        'cisco.dcnm.dcnm_network',
    })

    def _execute_ndfc_module(self, module_name, state, config, deploy=None, fabric_param='fabric'):
        """
        Execute an NDFC Ansible module via _execute_module.

        Supports configurable fabric parameter name to handle both
        standard modules (fabric:) and dcnm_vpc_pair (src_fabric:).

        Args:
            module_name: Fully qualified module name (e.g., cisco.dcnm.dcnm_vrf).
            state: Module state parameter.
            config: Configuration data to send.
            deploy: Whether to deploy (None = omit parameter).
            fabric_param: Fabric parameter name ('fabric' or 'src_fabric').

        Returns:
            Module result dict.
        """
        module_args = {
            fabric_param: self.fabric_name,
            'state': state,
            'config': config,
        }
        if deploy is not None:
            module_args['deploy'] = deploy

        if module_name in self.MODULES_WITH_ACTION_PLUGINS:
            return self._execute_via_action_plugin(module_name, module_args)

        return self.action_module._execute_module(
            module_name=module_name,
            module_args=module_args,
            task_vars=self.task_vars,
            tmp=self.tmp,
        )

    def _execute_via_action_plugin(self, module_name, module_args):
        """
        Execute an NDFC module through its companion action plugin.

        Some NDFC modules (dcnm_vrf, dcnm_network) have action plugins that
        perform fabric discovery and inject metadata before running the module.
        Ansible's task executor invokes these automatically for native tasks.
        This method replicates that routing for programmatic calls.

        Args:
            module_name: Fully qualified module name (e.g. 'cisco.dcnm.dcnm_vrf').
            module_args: Dict of module arguments (fabric, state, config, etc.).

        Returns:
            Module result dict.
        """
        original_args = self.action_module._task.args
        original_action = self.action_module._task.action

        try:
            self.action_module._task.args = module_args
            self.action_module._task.action = module_name

            action_plugin = self.action_module._shared_loader_obj.action_loader.get(
                module_name,
                task=self.action_module._task,
                connection=self.action_module._connection,
                play_context=self.action_module._play_context,
                loader=self.action_module._loader,
                templar=self.action_module._templar,
                shared_loader_obj=self.action_module._shared_loader_obj,
            )

            return action_plugin.run(task_vars=self.task_vars, tmp=self.tmp)
        finally:
            self.action_module._task.args = original_args
            self.action_module._task.action = original_action

    # ══════════════════════════════════════════════════════════════════════════
    # Internal Methods (called from pipeline via '_' prefix)
    # ══════════════════════════════════════════════════════════════════════════

    def _prepare_msite_data(self, resource_name, step):
        """
        Prepare multisite data for MSD/MCFG removal operations.

        Delegates to the existing prepare_msite_data action plugin.
        """
        return self.action_module._execute_module(
            module_name="cisco.nac_dc_vxlan.dtc.prepare_msite_data",
            module_args={
                "data_model": self.data_model,
                "parent_fabric": self.fabric_name,
                "parent_fabric_type": self.fabric_type,
                "nd_version": self.task_vars.get('nd_version', ''),
            },
            task_vars=self.task_vars,
            tmp=self.tmp,
        )

    def _manage_child_fabrics(self, resource_name, step):
        """
        Manage child fabric associations for MSD/MCFG removal.

        Delegates to the existing manage_child_fabrics action plugin.
        """
        return self.action_module._execute_module(
            module_name="cisco.nac_dc_vxlan.dtc.manage_child_fabrics",
            module_args={
                "data_model": self.data_model,
                "operation": "remove",
            },
            task_vars=self.task_vars,
            tmp=self.tmp,
        )


class ActionModule(ActionBase):
    """
    Ansible ActionBase wrapper for remove_resources.

    Handles parameter validation, error handling, and delegation
    to the ResourceRemover domain class.
    """

    REQUIRED_PARAMS = ['fabric_type', 'fabric_name', 'data_model', 'resource_data', 'change_flags']

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

        # Run registry validation at verbose level
        if display.verbosity >= 3:
            collection_path = RegistryLoader.get_collection_path()
            validation = RegistryLoader.validate_all(collection_path)
            if not validation['valid']:
                display.warning(
                    f"Registry validation errors: {validation['errors']}"
                )
            if validation['warnings']:
                display.warning(
                    f"Registry validation warnings: {validation['warnings']}"
                )

        try:
            remover = ResourceRemover(params, self, task_vars, tmp)
            result = remover.remove()

            results.update(result)
            if result.get('failed'):
                results['failed'] = True
            else:
                # Set changed if any step reported changes
                results['changed'] = any(
                    r.get('changed', False) for r in result.get('results', [])
                )

        except Exception as e:
            results['failed'] = True
            results['msg'] = f"Remove resources failed: {str(e)}"

        return results

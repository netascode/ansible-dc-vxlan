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
Pipeline Base — Abstract base class for data-driven NDFC pipeline execution.

Provides the shared pipeline iteration skeleton using the Template Method
pattern. Concrete subclasses (ResourceManager, ResourceRemover) implement
data resolution strategy and any additional guard logic.

Shared infrastructure includes:
  - Pipeline lookup and tag filtering
  - Change flag guard checking
  - Internal method dispatch (module names starting with '_')
  - NDFC module execution delegation to NdfcModuleExecutor
  - Shared internal methods:
      _update_switch_hostname_policy — hostname policy management
      _prepare_msite_data — multisite data preparation
      _manage_child_fabrics — child fabric association management
      _vrf_loopback_attach — VRF loopback attachment via REST
      _tor_pairing — ToR pairing create/remove (direct or discovery mode)
      _unmanaged_policy — discover and remove unmanaged policies from NDFC
      _config_save — delegates to fabric_deploy_manager (operation: config_save)
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import time
from abc import ABC, abstractmethod

from ansible.utils.display import Display

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.registry_loader import (
    RegistryLoader,
)

display = Display()


class PipelineRunnerBase(ABC):
    """
    Abstract base for data-driven NDFC pipeline execution.

    Provides the shared pipeline iteration skeleton. Concrete subclasses
    implement data resolution strategy and any additional guard logic.

    Class Attributes:
        REGISTRY_KEY: Registry file key ('create_resources' or 'remove_resources').
        OPERATION: Operation name ('create' or 'remove') for logging and msite dispatch.
    """

    # Subclasses must set these
    REGISTRY_KEY = None
    OPERATION = None

    def __init__(self, params, executor, task_vars):
        """
        Initialize the pipeline runner.

        Args:
            params: Dict of task args from the role task YAML.
            executor: NdfcModuleExecutor instance (injected).
            task_vars: Ansible task variables.
        """
        self.fabric_type = params['fabric_type']
        self.fabric_name = params['fabric_name']
        self.data_model = params['data_model']
        self.resource_data = params['resource_data']
        self.change_flags = params['change_flags']
        self.run_map_diff_run = params.get('run_map_diff_run', True)
        self.force_run_all = params.get('force_run_all', False)
        self.executor = executor
        self.task_vars = task_vars

        # Load pipeline from registry
        collection_path = RegistryLoader.get_collection_path()
        registry = RegistryLoader.load(collection_path, self.REGISTRY_KEY)
        self.pipelines = registry.get(self.REGISTRY_KEY, {})

    def run_pipeline(self):
        """
        Execute the ordered pipeline for the current fabric type.

        Template method: filter → iterate → guard → dispatch → execute.

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
                'msg': (
                    f"No {self.OPERATION} pipeline defined for "
                    f"fabric type: {self.fabric_type}"
                ),
            }

        # Filter by tags if needed
        ansible_run_tags = self.task_vars.get('ansible_run_tags', [])
        pipeline = RegistryLoader.filter_pipeline_by_tags(pipeline, ansible_run_tags)

        # Hook: subclass pre-pipeline setup (e.g., pre-fetch switch list)
        context = self._pre_pipeline_setup()

        step_results = []
        total_steps = len(pipeline)
        pipeline_start = time.monotonic()

        for step_index, step in enumerate(pipeline, 1):
            resource_name = step['resource_name']
            module = step['module']
            flag_name = step.get('change_flag_guard')
            step_start = time.monotonic()
            op_label = self.OPERATION.upper()

            display.display(
                f"\n{'─' * 60}\n"
                f"{op_label} [{self.fabric_name}] "
                f"Step {step_index}/{total_steps}: {resource_name} ({module})\n"
                f"{'─' * 60}",
                color='cyan',
            )

            # ── Hook: subclass-specific additional guards ─────────────────
            guard_result = self._check_additional_guards(step, context)
            if guard_result is not None:
                step_results.append(guard_result)
                elapsed = time.monotonic() - step_start
                reason = guard_result.get('reason', 'guard')
                display.display(
                    f"{op_label} [{self.fabric_name}] "
                    f"{resource_name} → skipped ({reason}) [{elapsed:.1f}s]",
                    color='yellow',
                )
                continue

            # ── Guard: data_model_guard ───────────────────────────────────
            dm_guard = step.get('data_model_guard')
            if dm_guard:
                value = self._evaluate_data_model_guard(dm_guard)
                if not value:
                    step_results.append({
                        'resource_name': resource_name,
                        'module': module,
                        'status': 'skipped',
                        'reason': f"data_model_guard '{dm_guard}' resolved to falsy",
                    })
                    elapsed = time.monotonic() - step_start
                    display.display(
                        f"{op_label} [{self.fabric_name}] "
                        f"{resource_name} → skipped (data_model_guard) [{elapsed:.1f}s]",
                        color='yellow',
                    )
                    continue

            # ── Guard: change_flag_guard ──────────────────────────────────
            if flag_name and not self.change_flags.get(flag_name, False):
                step_results.append({
                    'resource_name': resource_name,
                    'module': module,
                    'status': 'skipped',
                    'reason': f"change flag '{flag_name}' is False",
                })
                elapsed = time.monotonic() - step_start
                display.display(
                    f"{op_label} [{self.fabric_name}] "
                    f"{resource_name} → skipped (no changes) [{elapsed:.1f}s]",
                    color='yellow',
                )
                continue

            # ── Internal method dispatch ──────────────────────────────────
            if isinstance(module, str) and module.startswith('_'):
                result = self._dispatch_internal_method(resource_name, module, step)
                step_results.append(result)
                elapsed = time.monotonic() - step_start
                status = result.get('status', 'ok')
                display.display(
                    f"{op_label} [{self.fabric_name}] "
                    f"{resource_name} → {status} [{elapsed:.1f}s]",
                    color='green' if status != 'failed' else 'red',
                )
                if status == 'failed':
                    return {
                        'results': step_results,
                        'failed': True,
                        'msg': result.get('reason', f"Internal method '{module}' failed"),
                    }
                continue

            # ── Hook: subclass data resolution ────────────────────────────
            data, resolved_state = self._resolve_step_data(resource_name, step)

            if not data:
                step_results.append({
                    'resource_name': resource_name,
                    'module': module,
                    'status': 'skipped',
                    'reason': 'no data available',
                })
                elapsed = time.monotonic() - step_start
                display.display(
                    f"{op_label} [{self.fabric_name}] "
                    f"{resource_name} → skipped (no data) [{elapsed:.1f}s]",
                    color='yellow',
                )
                continue

            # ── Fabric parameter resolution ───────────────────────────────
            fabric_param = step.get('fabric_param', 'fabric')

            # ── Execute NDFC module ───────────────────────────────────────
            save = step.get('save')
            deploy = step.get('deploy')

            display.v(
                f"{op_label} [{self.fabric_name}] Executing {module} for "
                f"{resource_name} with state={resolved_state}, save={save}, deploy={deploy}, "
                f"items={len(data) if isinstance(data, list) else '?'}"
            )

            result = self.executor.execute(
                module_name=f"cisco.dcnm.{module}",
                state=resolved_state,
                config=data,
                fabric_name=self.fabric_name,
                save=save,
                deploy=deploy,
                fabric_param=fabric_param,
            )

            elapsed = time.monotonic() - step_start

            if result.get('failed'):
                display.display(
                    f"{op_label} [{self.fabric_name}] "
                    f"{resource_name} → failed [{elapsed:.1f}s]",
                    color='red',
                )
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
                        f"{self.OPERATION.title()} pipeline failed at step "
                        f"'{resource_name}' ({module}): "
                        f"{result.get('msg', 'unknown error')}"
                    ),
                }

            changed = result.get('changed', False)
            display.display(
                f"{op_label} [{self.fabric_name}] "
                f"{resource_name} → ok (changed={changed}) [{elapsed:.1f}s]",
                color='yellow' if changed else 'green',
            )

            step_results.append({
                'resource_name': resource_name,
                'module': module,
                'status': 'ok',
                'changed': changed,
                'result': result,
            })

        pipeline_elapsed = time.monotonic() - pipeline_start
        display.display(
            f"\n{'═' * 60}\n"
            f"{self.OPERATION.upper()} [{self.fabric_name}] "
            f"Pipeline complete — {total_steps} steps in {pipeline_elapsed:.1f}s\n"
            f"{'═' * 60}",
            color='cyan',
        )

        return {
            'results': step_results,
            'failed': False,
            'msg': (
                f"{self.OPERATION.title()} pipeline completed for "
                f"{self.fabric_type} fabric '{self.fabric_name}'"
            ),
        }

    # ══════════════════════════════════════════════════════════════════════════
    # Subclass Hooks
    # ══════════════════════════════════════════════════════════════════════════

    def _pre_pipeline_setup(self):
        """
        Hook for subclass pre-pipeline initialization.

        Called once before the pipeline loop begins. Override to perform
        setup like pre-fetching switch lists.

        Returns:
            Context dict passed to _check_additional_guards for each step.
        """
        return {}

    def _check_additional_guards(self, step, context):
        """
        Hook for subclass-specific guards beyond change_flag_guard.

        Called for each step before the change_flag_guard check. Override
        to add guards like delete_mode_guard, skip_if_child_fabric, etc.

        Args:
            step: Pipeline step dict.
            context: Dict returned by _pre_pipeline_setup.

        Returns:
            A skip result dict to append to step_results if the step should
            be skipped, or None to proceed with the step.
        """
        return None

    @abstractmethod
    def _resolve_step_data(self, resource_name, step):
        """
        Resolve data and state for a pipeline step.

        Create resolves diff.updated preference; remove resolves diff.removed
        with dual-state (deleted vs overridden).

        Args:
            resource_name: Logical name of the resource.
            step: Pipeline step dict from the YAML registry.

        Returns:
            Tuple of (data_list, resolved_state_string).
        """

    # ══════════════════════════════════════════════════════════════════════════
    # Shared Infrastructure
    # ══════════════════════════════════════════════════════════════════════════

    def _dispatch_internal_method(self, resource_name, module, step):
        """
        Dispatch to an internal method by name.

        Internal methods are pipeline steps where module starts with '_'.
        They are resolved via getattr on the runner class hierarchy.

        Args:
            resource_name: Logical name of the resource.
            module: Internal method name (e.g. '_config_save').
            step: Pipeline step dict.

        Returns:
            Step result dict with status 'ok' or 'failed'.
        """
        try:
            method = getattr(self, module)
            result = method(resource_name, step)
            entry = {
                'resource_name': resource_name,
                'module': module,
                'status': 'ok',
                'result': result,
            }
            # Internal methods can signal failure
            if isinstance(result, dict) and result.get('failed'):
                entry['status'] = 'failed'
                entry['reason'] = result.get('msg', f"Internal method '{module}' failed")
            return entry
        except AttributeError:
            return {
                'resource_name': resource_name,
                'module': module,
                'status': 'failed',
                'reason': f"Internal method '{module}' not found on {self.__class__.__name__}",
            }

    def _evaluate_data_model_guard(self, dotpath):
        """
        Traverse the data model by dotpath and return the resolved value.

        Used by the data_model_guard pipeline field. The caller checks
        truthiness of the returned value to decide whether to skip the step.

        Args:
            dotpath: Dot-separated path into the data model
                     (e.g. 'vxlan.overlay.vrfs').

        Returns:
            The resolved value, or None if any key in the path is missing.
        """
        obj = self.data_model
        for key in dotpath.split('.'):
            if not isinstance(obj, dict):
                return None
            obj = obj.get(key)
            if obj is None:
                return None
        return obj

    # ══════════════════════════════════════════════════════════════════════════
    # Shared Internal Methods (called from pipeline via '_' prefix)
    # ══════════════════════════════════════════════════════════════════════════

    def _update_switch_hostname_policy(self, resource_name, step):
        """
        Manage hostname policy on switches

        Delegates to the existing update_switch_hostname_policy action plugin.
        """
        return self.executor.execute_plugin(
            module_name="cisco.nac_dc_vxlan.dtc.update_switch_hostname_policy",
            module_args={
                "data_model": self.data_model,
                "template_name": "host_11_1",
            },
        )

    def _prepare_msite_data(self, resource_name, step):
        """
        Prepare multisite data for MSD/MCFG operations.

        Delegates to the existing prepare_msite_data action plugin.
        Operation type is determined by the OPERATION class attribute.
        """
        return self.executor.execute_plugin(
            module_name="cisco.nac_dc_vxlan.dtc.prepare_msite_data",
            module_args={
                "data_model": self.data_model,
                "parent_fabric": self.fabric_name,
                "parent_fabric_type": self.fabric_type,
                "nd_version": self.task_vars.get('nd_version', ''),
            },
        )

    def _manage_child_fabrics(self, resource_name, step):
        """
        Manage child fabric associations for MSD/MCFG operations.

        Delegates to the existing manage_child_fabrics action plugin.
        Operation type is determined by the OPERATION class attribute.
        """
        return self.executor.execute_plugin(
            module_name="cisco.nac_dc_vxlan.dtc.manage_child_fabrics",
            module_args={
                "data_model": self.data_model,
                "operation": self.OPERATION,
            },
        )

    def _vrf_loopback_attach(self, resource_name, step):
        """
        Attach loopbacks to VRFs via NDFC REST API.

        Resolves the correct REST endpoint per fabric type:
          - MCFG: /onemanage/appcenter/cisco/ndfc/api/v1/onemanage/top-down/fabrics/{fabric}/vrfs/attachments
          - All others: /appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/v2/fabrics/{fabric}/vrfs/attachments
        """
        import json

        resource_entry = self.resource_data.get('vrf_loopback_attach', {})
        data = resource_entry.get('module_data', resource_entry.get('data', []))

        if not data:
            return {'failed': False, 'msg': 'No VRF loopback attach data — skipped'}

        if self.fabric_type == 'MCFG':
            path = (
                f"/onemanage/appcenter/cisco/ndfc/api/v1/onemanage/top-down"
                f"/fabrics/{self.fabric_name}/vrfs/attachments"
            )
        else:
            path = (
                f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/v2"
                f"/fabrics/{self.fabric_name}/vrfs/attachments"
            )

        display.v(
            f"{self.OPERATION.upper()} [{self.fabric_name}] Attaching loopbacks to VRFs "
            f"via REST POST ({len(data) if isinstance(data, list) else '?'} items)"
        )

        return self.executor.execute_rest("POST", path, json_data=json.dumps(data))

    def _tor_pairing(self, resource_name, step):
        """
        Create or remove ToR pairings in NDFC.

        Direction is determined by self.OPERATION ('create' or 'remove'):
          - create: Uses diff.updated from build_resource_data
          - remove: Uses diff.removed from build_resource_data

        Diff run active:  Passes pre-computed diff items via 'pairings' param
                          (direct mode).
        Diff run disabled: Passes leaf_serial_number + current_pairings and lets
                          the plugin discover, diff, and execute (discovery mode).
        """
        # diff_compare returns 'updated' (new/changed) and 'removed' keys
        diff_key = 'updated' if self.OPERATION == 'create' else 'removed'
        op_label = self.OPERATION.upper()

        resource_entry = self.resource_data.get('tor_pairing', {})
        tor_pairing_data = resource_entry.get('module_data', resource_entry.get('data', []))

        # For create: skip if no pairing data at all
        # For remove: still need to proceed when diff_run is disabled (NDFC may have stale pairings)
        if not tor_pairing_data:
            if self.OPERATION == 'create' or (self.run_map_diff_run and not self.force_run_all):
                return {'failed': False, 'msg': 'No ToR pairing data — skipped'}

        if self.run_map_diff_run and not self.force_run_all:
            # Diff run active — items pre-computed by build_resource_data (direct mode)
            diff = resource_entry.get('diff')
            items = diff.get(diff_key, []) if diff and isinstance(diff, dict) else []

            if not items:
                display.v(
                    f"{op_label} [{self.fabric_name}] No ToR pairings to "
                    f"{self.OPERATION} — skipped"
                )
                return {'failed': False, 'msg': f'No ToR pairings to {self.OPERATION}'}

            display.v(
                f"{op_label} [{self.fabric_name}] {self.OPERATION.title()}ing "
                f"{len(items)} ToR pairing(s)"
            )

            return self.executor.execute_plugin(
                module_name="cisco.nac_dc_vxlan.dtc.process_tor_pairing",
                module_args={
                    "operation": self.OPERATION,
                    "pairings": items,
                    "fabric_name": self.fabric_name,
                },
            )
        else:
            # Diff run disabled — discover + diff + execute (discovery mode)
            switches = self.data_model.get('vxlan', {}).get('topology', {}).get('switches', [])
            leaf_switches = [s for s in switches if s.get('role') == 'leaf']

            if not leaf_switches:
                display.v(
                    f"{op_label} [{self.fabric_name}] No leaf switches found — skipped"
                )
                return {'failed': False, 'msg': 'No leaf switches found — skipped'}

            display.v(
                f"{op_label} [{self.fabric_name}] Discovering and "
                f"{self.OPERATION}ing ToR pairings"
            )

            return self.executor.execute_plugin(
                module_name="cisco.nac_dc_vxlan.dtc.process_tor_pairing",
                module_args={
                    "operation": self.OPERATION,
                    "fabric_name": self.fabric_name,
                    "leaf_serial_number": leaf_switches[0].get('serial_number', ''),
                    "current_pairings": tor_pairing_data if tor_pairing_data else [],
                },
            )

    def _unmanaged_policy(self, resource_name, step):
        """
        Discover and remove unmanaged policies from NDFC.

        Queries each switch for policies with the 'nac_' description prefix,
        compares against the data model, and deletes any that are not declared.
        Delegates to the unmanaged_policy action plugin which handles both
        discovery and dcnm_policy deletion in a single call.

        Requires switch serial numbers from the pre-fetched switch list
        (populated by _pre_pipeline_setup on the remove subclass, stored
        as self.fabric_switch_list).
        """
        switches = getattr(self, 'fabric_switch_list', [])
        if not switches:
            return {'failed': False, 'msg': 'No switches in fabric — skipped'}

        serial_numbers = [
            s['serialNumber'] for s in switches
            if isinstance(s, dict) and 'serialNumber' in s
        ]

        if not serial_numbers:
            return {'failed': False, 'msg': 'No switch serial numbers found — skipped'}

        display.v(
            f"{self.OPERATION.upper()} [{self.fabric_name}] Discovering and removing "
            f"unmanaged policies across {len(serial_numbers)} switch(es)"
        )

        return self.executor.execute_plugin(
            module_name="cisco.nac_dc_vxlan.dtc.unmanaged_policy",
            module_args={
                "switch_serial_numbers": serial_numbers,
                "data_model": self.data_model,
                "fabric_name": self.fabric_name,
            },
        )

    def _config_save(self, resource_name, step):
        """
        Execute a config-save via the fabric_deploy_manager action plugin.

        Delegates to fabric_deploy_manager with operation='config_save',
        consolidating config-save into a single code path. The fabric_deploy_manager
        handles MCFG vs standard path resolution via ApiPathResolver.

        Treats HTTP 500 as non-fatal since config-save can return 500
        when there are no pending changes (matches original rescue block behavior).
        """
        result = self.executor.execute_plugin(
            module_name="cisco.nac_dc_vxlan.dtc.fabric_deploy_manager",
            module_args={
                "fabric_name": self.fabric_name,
                "fabric_type": self.fabric_type,
                "operation": "config_save",
            },
        )

        if result.get('failed'):
            return_code = None
            try:
                return_code = result.get('msg', {}).get('RETURN_CODE')
            except (AttributeError, TypeError):
                pass

            if return_code == 500:
                display.v(
                    f"{self.OPERATION.upper()} [{self.fabric_name}] Config-save returned "
                    f"HTTP 500 (non-fatal — no pending changes)"
                )
                return {'failed': False, 'msg': 'Config-save HTTP 500 (non-fatal)'}

        return result

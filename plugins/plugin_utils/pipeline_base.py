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
Pipeline Base — Abstract base class for data-driven NDFC pipeline execution.

Provides the shared pipeline iteration skeleton using the Template Method
pattern. Concrete subclasses (ResourceManager, ResourceRemover) implement
data resolution strategy and any additional guard logic.

Shared infrastructure includes:
  - Pipeline lookup and tag filtering
  - Change flag guard checking
  - Internal method dispatch (module names starting with '_')
  - NDFC module execution delegation to NdfcModuleExecutor
  - Shared internal methods (_prepare_msite_data, _manage_child_fabrics, _config_save)
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

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
        REGISTRY_KEY: Registry file key ('create_pipelines' or 'remove_pipelines').
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

        for step in pipeline:
            resource_name = step['resource_name']
            module = step['module']
            flag_name = step.get('change_flag_guard')

            # ── Hook: subclass-specific additional guards ─────────────────
            guard_result = self._check_additional_guards(step, context)
            if guard_result is not None:
                step_results.append(guard_result)
                continue

            # ── Guard: change_flag_guard ──────────────────────────────────
            if flag_name and not self.change_flags.get(flag_name, False):
                step_results.append({
                    'resource_name': resource_name,
                    'module': module,
                    'status': 'skipped',
                    'reason': f"change flag '{flag_name}' is False",
                })
                continue

            # ── Internal method dispatch ──────────────────────────────────
            if isinstance(module, str) and module.startswith('_'):
                result = self._dispatch_internal_method(resource_name, module, step)
                step_results.append(result)
                if result.get('status') == 'failed':
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
                continue

            # ── Fabric parameter resolution ───────────────────────────────
            fabric_param = step.get('fabric_param', 'fabric')

            # ── Execute NDFC module ───────────────────────────────────────
            deploy = step.get('deploy')

            display.v(
                f"{self.OPERATION.upper()} [{self.fabric_name}] Executing {module} for "
                f"{resource_name} with state={resolved_state}, deploy={deploy}, "
                f"items={len(data) if isinstance(data, list) else '?'}"
            )

            result = self.executor.execute(
                module_name=f"cisco.dcnm.{module}",
                state=resolved_state,
                config=data,
                fabric_name=self.fabric_name,
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
                        f"{self.OPERATION.title()} pipeline failed at step "
                        f"'{resource_name}' ({module}): "
                        f"{result.get('msg', 'unknown error')}"
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

    def _config_save(self, resource_name, step):
        """
        Execute a config-save POST to NDFC.

        Treats HTTP 500 as non-fatal since config-save can return 500
        when there are no pending changes (matches original rescue block behavior).
        """
        path = (
            f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control"
            f"/fabrics/{self.fabric_name}/config-save"
        )

        result = self.executor.execute_rest("POST", path)

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

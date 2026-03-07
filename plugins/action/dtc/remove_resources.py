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

import inspect

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.registry_loader import RegistryLoader

display = Display()


class ResourceRemover:
    """
    Manages the ordered removal of unmanaged NDFC resources for any fabric type.

    Replaces the dtc/remove role's per-fabric-type sub_main files and the
    conditional cisco.dcnm module calls scattered across ~10 task files.

    Removal order is the REVERSE of creation to respect dependencies
    (e.g., remove networks before VRFs, remove interfaces before switches).

    Pipeline definitions are loaded from objects/remove_pipelines.yml via
    the RegistryLoader utility. Each pipeline step specifies:
      - resource_name:     Which resource data to send
      - module:            Which cisco.dcnm module to call (or internal method)
      - state:             Module state parameter (deleted, overridden, etc.)
      - change_flag_guard: Only execute if this change flag is True

    Adding a new removal step requires only editing remove_pipelines.yml —
    no Python changes needed.
    """

    def __init__(self, params):
        self.class_name = self.__class__.__name__

        # Fabric parameters
        self.fabric_type = params['fabric_type']
        self.fabric_name = params['fabric_name']
        self.data_model = params['data_model']

        # Resource data and change flags from the common role (build_resource_data)
        self.resource_data = params['resource_data']
        self.change_flags = params['change_flags']

        # Execution control parameters
        self.run_map_diff_run = params.get('run_map_diff_run', True)
        self.force_run_all = params.get('force_run_all', False)
        self.interface_delete_mode = params.get('interface_delete_mode', False)
        self.stage_remove = params.get('stage_remove', False)

        # Active Ansible tags for per-step filtering
        self.active_tags = params.get('active_tags', [])

        # Ansible execution context
        self.task_vars = params['task_vars']
        self.tmp = params['tmp']
        self.action_module = params['action_module']

        # Load pipeline registry from external YAML
        self.collection_path = RegistryLoader.get_collection_path()
        registry = RegistryLoader.load(self.collection_path, 'remove_pipelines')
        self.pipelines = registry.get('remove_pipelines', {})

        # Extract the role-level bypass tag from registry
        # (e.g., 'role_remove' — when present in --tags, runs full pipeline)
        self.role_tag = self.pipelines.pop('role_tag', None)

    def remove(self):
        """
        Execute the ordered removal pipeline for the current fabric type.

        Iterates through the pipeline steps defined in remove_pipelines.yml,
        checking change flag guards and data availability. Interface removal
        has special handling based on diff_run mode and interface_delete_mode.

        Returns:
            dict with keys:
                - results: list of {resource_name, module, status, response}
                - failed: bool indicating if any step failed
                - msg: error message if failed
        """
        method_name = inspect.stack()[0][3]
        display.banner(
            f"{self.class_name}.{method_name}() "
            f"Fabric: ({self.fabric_name}) Type: ({self.fabric_type})"
        )

        pipeline = self.pipelines.get(self.fabric_type)
        if pipeline is None:
            return {
                'failed': True,
                'msg': f"No remove pipeline defined for fabric type '{self.fabric_type}'",
                'results': [],
            }

        # Filter pipeline steps by active tags
        pipeline = RegistryLoader.filter_pipeline_by_tags(
            pipeline, self.active_tags, self.role_tag
        )

        display.v(
            f"{self.class_name}: Pipeline has {len(pipeline)} steps "
            f"after tag filtering (active_tags={self.active_tags}, role_tag={self.role_tag})"
        )

        # Get the list of switches from NDFC for conditional checks
        switch_list = self._get_fabric_switches()

        step_results = []

        for step in pipeline:
            resource_name = step['resource_name']
            module = step['module']
            state = step.get('state')
            flag_name = step.get('change_flag_guard')

            # Check change flag guard — skip if flag is False
            if flag_name and not self.change_flags.get(flag_name, False):
                display.v(
                    f"{self.class_name}: Skipping removal of '{resource_name}' — "
                    f"change flag '{flag_name}' is False"
                )
                step_results.append({
                    'resource_name': resource_name,
                    'module': module,
                    'status': 'skipped',
                    'reason': f'change_flag_guard {flag_name} is False',
                })
                continue

            # Special handling for interfaces
            if resource_name == 'interfaces':
                result = self._handle_interface_removal(switch_list)
                step_results.append({
                    'resource_name': resource_name,
                    'module': module,
                    'status': 'ok' if not result.get('failed') else 'failed',
                    'response': result,
                })
                if result.get('failed'):
                    return {
                        'failed': True,
                        'msg': f"Interface removal failed: {result.get('msg')}",
                        'results': step_results,
                    }
                continue

            # Internal method call (prefixed with '_')
            if module.startswith('_'):
                display.v(f"{self.class_name}: Executing internal method '{module}' for '{resource_name}'")
                try:
                    result = getattr(self, module)(resource_name)
                    step_results.append({
                        'resource_name': resource_name,
                        'module': module,
                        'status': 'ok',
                        'response': result,
                    })
                except Exception as e:
                    display.warning(
                        f"{self.class_name}: Internal method '{module}' failed for "
                        f"'{resource_name}': {str(e)}"
                    )
                    step_results.append({
                        'resource_name': resource_name,
                        'module': module,
                        'status': 'failed',
                        'msg': str(e),
                    })
                continue

            # Determine removal data — prefer diff.removed, fall back to full data
            data = self._get_removal_data(resource_name)

            # Skip if no data to remove
            if not data:
                display.v(
                    f"{self.class_name}: Skipping removal of '{resource_name}' — no data to remove"
                )
                step_results.append({
                    'resource_name': resource_name,
                    'module': module,
                    'status': 'skipped',
                    'reason': 'no removal data',
                })
                continue

            # Execute the NDFC module
            display.v(
                f"{self.class_name}: Executing '{module}' with state='{state}' "
                f"for removal of '{resource_name}' ({len(data) if isinstance(data, list) else 1} items)"
            )

            result = self._execute_ndfc_module(
                module_name=f"cisco.dcnm.{module}",
                state=state,
                config=data,
                deploy=False,  # Remove role does not deploy inline — deploy is a separate step
            )

            if result.get('failed'):
                display.warning(
                    f"{self.class_name}: Module '{module}' failed for removal of '{resource_name}': "
                    f"{result.get('msg', 'unknown error')}"
                )
                step_results.append({
                    'resource_name': resource_name,
                    'module': module,
                    'status': 'failed',
                    'msg': result.get('msg'),
                    'response': result,
                })
                return {
                    'failed': True,
                    'msg': f"Remove pipeline failed at step '{resource_name}': {result.get('msg')}",
                    'results': step_results,
                }

            step_results.append({
                'resource_name': resource_name,
                'module': module,
                'status': 'ok',
                'response': result,
            })

        return {
            'failed': False,
            'results': step_results,
        }

    # =========================================================================
    # Data Resolution
    # =========================================================================

    def _get_removal_data(self, resource_name):
        """
        Determine the data set to use for resource removal.

        When diff_run is active and force_run_all is False, uses the
        diff.removed list (items that existed in the previous run but
        are no longer in the current data model). Otherwise, uses the
        full resource data set.

        Args:
            resource_name: Logical name of the resource

        Returns:
            list of items to remove, or empty list if nothing to remove
        """
        resource_entry = self.resource_data.get(resource_name, {})
        if not isinstance(resource_entry, dict):
            return resource_entry if resource_entry else []

        # For diff-based runs, prefer the diff.removed list
        if self.run_map_diff_run and not self.force_run_all:
            diff = resource_entry.get('diff')
            if diff and isinstance(diff, dict):
                removed = diff.get('removed', [])
                if removed:
                    return removed

        # Fall back to full data
        return resource_entry.get('data', [])

    def _get_fabric_switches(self):
        """
        Get the list of switches registered to this fabric from NDFC.

        Used for conditional checks (e.g., only attempt interface removal
        if switches exist in the fabric).

        Returns:
            list of switch data dicts from NDFC, or empty list on error
        """
        path = (
            f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/"
            f"control/fabrics/{self.fabric_name}/inventory/switchesByFabric"
        )

        result = self.action_module._execute_module(
            module_name="cisco.dcnm.dcnm_rest",
            module_args={
                "method": "GET",
                "path": path,
            },
            task_vars=self.task_vars,
            tmp=self.tmp,
        )

        # Extract switch list from response
        response = result
        if 'response' in result:
            response = result['response']
        if 'msg' in response and isinstance(response['msg'], dict):
            response = response['msg']

        return response.get('DATA', []) if isinstance(response, dict) else []

    # =========================================================================
    # Interface Removal (Special Handling)
    # =========================================================================

    def _handle_interface_removal(self, switch_list):
        """
        Handle interface removal with mode-specific logic.

        Replicates the conditional interface removal from the remove role's
        common/interfaces.yml task file, supporting two modes:

        1. Diff Run active (run_map_diff_run=True, force_run_all=False):
           - Uses diff.removed list → state: deleted
           - Removes only interfaces that were removed from the data model

        2. Full run (diff_run disabled or force_run_all=True):
           - Uses data_remove_overridden list → state: overridden
           - Ensures only data-model-defined interfaces exist on the fabric

        Args:
            switch_list: List of switches from NDFC

        Returns:
            dict with execution result
        """
        # Skip if no switches in the fabric
        if not switch_list:
            display.v(f"{self.class_name}: No switches in fabric, skipping interface removal")
            return {'failed': False, 'skipped': True, 'reason': 'no switches'}

        # Skip if interface_delete_mode is not enabled
        if not self.interface_delete_mode:
            display.v(f"{self.class_name}: interface_delete_mode is disabled, skipping interface removal")
            return {'failed': False, 'skipped': True, 'reason': 'interface_delete_mode disabled'}

        interface_data = self.resource_data.get('interface_all', {})
        if not isinstance(interface_data, dict):
            return {'failed': False, 'skipped': True, 'reason': 'no interface data'}

        # Determine mode and data
        if self.run_map_diff_run and not self.force_run_all:
            # Diff-based removal — delete only removed interfaces
            diff = interface_data.get('diff', {})
            config = diff.get('removed', []) if isinstance(diff, dict) else []
            state = 'deleted'
            mode = 'diff_run'
        else:
            # Full removal — override to only keep managed interfaces
            config = interface_data.get('data_remove_overridden', [])
            state = 'overridden'
            mode = 'full_run'

        if not config:
            display.v(
                f"{self.class_name}: No interfaces to remove in {mode} mode"
            )
            return {'failed': False, 'skipped': True, 'reason': f'no interfaces to remove ({mode})'}

        display.v(
            f"{self.class_name}: Removing interfaces in {mode} mode — "
            f"state={state}, {len(config)} interfaces"
        )

        result = self._execute_ndfc_module(
            module_name="cisco.dcnm.dcnm_interface",
            state=state,
            config=config,
            deploy=False,
        )

        return result

    # =========================================================================
    # NDFC Module Execution
    # =========================================================================

    def _execute_ndfc_module(self, module_name, state, config, deploy=None):
        """
        Execute an NDFC Ansible module via _execute_module.

        Args:
            module_name: Fully qualified module name (e.g., 'cisco.dcnm.dcnm_vrf')
            state: Module state parameter (deleted, overridden, etc.)
            config: Configuration data to pass to the module
            deploy: Optional deploy parameter (True/False)

        Returns:
            Module execution result dict
        """
        module_args = {
            'fabric': self.fabric_name,
            'state': state,
            'config': config,
        }

        if deploy is not None:
            module_args['deploy'] = deploy

        return self.action_module._execute_module(
            module_name=module_name,
            module_args=module_args,
            task_vars=self.task_vars,
            tmp=self.tmp,
        )


class ActionModule(ActionBase):
    """
    Action plugin: remove_resources

    Manages the ordered removal of unmanaged NDFC resources for any fabric
    type, replacing the dtc/remove role's 6 sub_main files and ~10 task
    files with a single pipeline-driven action plugin call.

    Removal order is the reverse of creation to respect dependencies.

    Parameters (from task args):
        fabric_type:          Fabric type (VXLAN_EVPN, eBGP_VXLAN, ISN, MSD, MCFG, External)
        fabric_name:          Name of the fabric
        data_model:           Extended data model (data_model_extended)
        resource_data:        Resource data from build_resource_data (vars_common)
        change_flags:         Change detection flags from build_resource_data
        run_map_diff_run:     Whether diff-based run is active
        force_run_all:        Force full run regardless of diff state
        interface_delete_mode: Whether interface deletion is enabled
        stage_remove:         Whether removal changes should be staged (not deployed)

    Returns:
        results:  List of per-step execution results
        failed:   Whether any step failed
    """

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False

        # Validate required parameters
        required_params = [
            'fabric_type', 'fabric_name', 'data_model',
            'resource_data', 'change_flags',
        ]
        for param in required_params:
            if self._task.args.get(param) is None:
                results['failed'] = True
                results['msg'] = f"Missing required parameter '{param}'"
                return results

        # Build params dict
        params = {
            'fabric_type': self._task.args['fabric_type'],
            'fabric_name': self._task.args['fabric_name'],
            'data_model': self._task.args['data_model'],
            'resource_data': self._task.args['resource_data'],
            'change_flags': self._task.args['change_flags'],
            'run_map_diff_run': self._task.args.get('run_map_diff_run', True),
            'force_run_all': self._task.args.get('force_run_all', False),
            'interface_delete_mode': self._task.args.get('interface_delete_mode', False),
            'stage_remove': self._task.args.get('stage_remove', False),
            'active_tags': task_vars.get('ansible_run_tags', []),
            'task_vars': task_vars,
            'tmp': tmp,
            'action_module': self,
        }

        try:
            remover = ResourceRemover(params)
            remove_result = remover.remove()

            results['results'] = remove_result.get('results', [])
            if remove_result.get('failed'):
                results['failed'] = True
                results['msg'] = remove_result.get('msg', 'Remove pipeline failed')

        except FileNotFoundError as e:
            results['failed'] = True
            results['msg'] = f"Remove pipeline failed — file not found: {str(e)}"
        except Exception as e:
            results['failed'] = True
            results['msg'] = f"Unexpected error during resource removal: {type(e).__name__}: {str(e)}"

        return results

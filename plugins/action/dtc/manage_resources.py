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


class ResourceManager:
    """
    Manages the ordered creation of NDFC resources for any fabric type.

    Replaces the dtc/create role's per-fabric-type sub_main files and the
    conditional cisco.dcnm module calls scattered across ~12 task files.

    Pipeline definitions are loaded from objects/create_pipelines.yml via
    the RegistryLoader utility. Each pipeline step specifies:
      - resource_name:     Which resource data to send
      - module:            Which cisco.dcnm module to call (or internal method)
      - state:             Module state parameter (merged, replaced, etc.)
      - change_flag_guard: Only execute if this change flag is True

    Adding a new creation step requires only editing create_pipelines.yml —
    no Python changes needed.
    """

    def __init__(self, params):
        self.class_name = self.__class__.__name__

        # Fabric parameters
        self.fabric_type = params['fabric_type']
        self.fabric_name = params['fabric_name']
        self.data_model = params['data_model']
        self.nd_version = params.get('nd_version')

        # Resource data and change flags from the common role (build_resource_data)
        self.resource_data = params['resource_data']
        self.change_flags = params['change_flags']

        # Active Ansible tags for per-step filtering
        self.active_tags = params.get('active_tags', [])

        # Ansible execution context
        self.task_vars = params['task_vars']
        self.tmp = params['tmp']
        self.action_module = params['action_module']

        # Load pipeline registry from external YAML
        self.collection_path = RegistryLoader.get_collection_path()
        registry = RegistryLoader.load(self.collection_path, 'create_pipelines')
        self.pipelines = registry.get('create_pipelines', {})

        # Extract the role-level bypass tag from registry
        # (e.g., 'role_create' — when present in --tags, runs full pipeline)
        self.role_tag = self.pipelines.pop('role_tag', None)

    def create(self):
        """
        Execute the ordered creation pipeline for the current fabric type.

        Iterates through the pipeline steps defined in create_pipelines.yml,
        checking change flag guards and data availability before executing
        each step.

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
                'msg': f"No create pipeline defined for fabric type '{self.fabric_type}'",
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

        step_results = []

        for step in pipeline:
            resource_name = step['resource_name']
            module = step['module']
            state = step.get('state')
            flag_name = step.get('change_flag_guard')

            # Check change flag guard — skip if flag is False
            if flag_name and not self.change_flags.get(flag_name, False):
                display.v(
                    f"{self.class_name}: Skipping '{resource_name}' — "
                    f"change flag '{flag_name}' is False"
                )
                step_results.append({
                    'resource_name': resource_name,
                    'module': module,
                    'status': 'skipped',
                    'reason': f'change_flag_guard {flag_name} is False',
                })
                continue

            # Get resource data for this step
            resource_entry = self.resource_data.get(resource_name, {})
            data = resource_entry.get('data', []) if isinstance(resource_entry, dict) else resource_entry

            # For diff-based runs, use diff.updated if available
            if isinstance(resource_entry, dict) and resource_entry.get('diff'):
                diff_data = resource_entry['diff'].get('updated')
                if diff_data is not None:
                    data = diff_data

            # Internal method call (prefixed with '_')
            if module.startswith('_'):
                display.v(f"{self.class_name}: Executing internal method '{module}' for '{resource_name}'")
                try:
                    result = getattr(self, module)(resource_name, data)
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

            # Skip if resource data is empty
            if not data:
                display.v(
                    f"{self.class_name}: Skipping '{resource_name}' — no data available"
                )
                step_results.append({
                    'resource_name': resource_name,
                    'module': module,
                    'status': 'skipped',
                    'reason': 'no data',
                })
                continue

            # Execute the NDFC module
            display.v(
                f"{self.class_name}: Executing '{module}' with state='{state}' "
                f"for '{resource_name}' ({len(data) if isinstance(data, list) else 1} items)"
            )

            result = self._execute_ndfc_module(
                module_name=f"cisco.dcnm.{module}",
                state=state,
                config=data,
            )

            if result.get('failed'):
                display.warning(
                    f"{self.class_name}: Module '{module}' failed for '{resource_name}': "
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
                    'msg': f"Create pipeline failed at step '{resource_name}': {result.get('msg')}",
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
    # NDFC Module Execution
    # =========================================================================

    def _execute_ndfc_module(self, module_name, state, config, deploy=None):
        """
        Execute an NDFC Ansible module via _execute_module.

        Follows the same pattern as fabric_deploy_manager.py for module
        execution through Ansible's action plugin interface.

        Args:
            module_name: Fully qualified module name (e.g., 'cisco.dcnm.dcnm_fabric')
            state: Module state parameter (merged, replaced, deleted, etc.)
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

    # =========================================================================
    # Internal Pipeline Methods (called when module starts with '_')
    # =========================================================================

    def _config_save(self, resource_name, data):
        """
        Execute a config-save POST to NDFC.

        Replicates the config-save block from the create role's sub_main files
        that triggers an NDFC config-save to propagate changes (e.g., after
        vPC peering updates).

        Args:
            resource_name: Logical name of the resource (for logging)
            data: Not used directly — config-save is fabric-level

        Returns:
            Module execution result dict
        """
        path = (
            f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/"
            f"control/fabrics/{self.fabric_name}/config-save"
        )

        display.v(f"{self.class_name}: Config-save for fabric '{self.fabric_name}'")

        result = self.action_module._execute_module(
            module_name="cisco.dcnm.dcnm_rest",
            module_args={
                "method": "POST",
                "path": path,
            },
            task_vars=self.task_vars,
            tmp=self.tmp,
        )

        # Handle known non-fatal error codes
        response = result
        if 'response' in result:
            response = result['response']
        if 'msg' in response:
            response = response['msg']

        if isinstance(response, dict) and response.get('RETURN_CODE') == 500:
            display.warning(
                f"{self.class_name}: Config-save returned 500 for fabric "
                f"'{self.fabric_name}': {response.get('DATA', 'no details')}"
            )
            # Config-save 500 is non-fatal (matches existing rescue block behavior)
            return {'failed': False, 'msg': 'config-save returned 500 (non-fatal)'}

        return result

    def _vrfs_networks_pipeline(self, resource_name, data):
        """
        Execute the VRF and Network creation sub-pipeline.

        VRFs and Networks have a specific ordering requirement:
        VRFs must be created before Networks that reference them.
        This method handles that ordering.

        Args:
            resource_name: 'vrfs_networks'
            data: Not used directly — reads from self.resource_data

        Returns:
            dict with VRF and Network results
        """
        results = {}

        # Create VRFs first
        vrf_data = self.resource_data.get('vrfs', {})
        vrf_config = vrf_data.get('data', []) if isinstance(vrf_data, dict) else vrf_data
        if vrf_config:
            display.v(f"{self.class_name}: Creating VRFs ({len(vrf_config)} items)")
            vrf_result = self._execute_ndfc_module(
                module_name="cisco.dcnm.dcnm_vrf",
                state="merged",
                config=vrf_config,
            )
            results['vrfs'] = vrf_result

            if vrf_result.get('failed'):
                return {'failed': True, 'msg': f"VRF creation failed: {vrf_result.get('msg')}", **results}

        # Then create Networks
        network_data = self.resource_data.get('networks', {})
        network_config = network_data.get('data', []) if isinstance(network_data, dict) else network_data
        if network_config:
            display.v(f"{self.class_name}: Creating Networks ({len(network_config)} items)")
            network_result = self._execute_ndfc_module(
                module_name="cisco.dcnm.dcnm_network",
                state="merged",
                config=network_config,
            )
            results['networks'] = network_result

            if network_result.get('failed'):
                return {'failed': True, 'msg': f"Network creation failed: {network_result.get('msg')}", **results}

        return {'failed': False, **results}

    def _prepare_msite_data(self, resource_name, data):
        """
        Prepare multi-site data for MSD/MCFG fabrics.

        Delegates to the existing prepare_msite_data action plugin.

        Args:
            resource_name: 'msite_data'
            data: Multi-site data to prepare

        Returns:
            Module execution result dict
        """
        return self.action_module._execute_module(
            module_name='cisco.nac_dc_vxlan.dtc.prepare_msite_data',
            module_args={
                'data_model': self.data_model,
                'resource_data': data,
            },
            task_vars=self.task_vars,
            tmp=self.tmp,
        )


class ActionModule(ActionBase):
    """
    Action plugin: manage_resources

    Manages the ordered creation of NDFC resources for any fabric type,
    replacing the dtc/create role's 6 sub_main files and ~12 task files
    with a single pipeline-driven action plugin call.

    Parameters (from task args):
        fabric_type:    Fabric type (VXLAN_EVPN, eBGP_VXLAN, ISN, MSD, MCFG, External)
        fabric_name:    Name of the fabric
        data_model:     Extended data model (data_model_extended)
        resource_data:  Resource data from build_resource_data (vars_common)
        change_flags:   Change detection flags from build_resource_data
        nd_version:     Nexus Dashboard version string

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
            'nd_version': self._task.args.get('nd_version'),
            'active_tags': task_vars.get('ansible_run_tags', []),
            'task_vars': task_vars,
            'tmp': tmp,
            'action_module': self,
        }

        try:
            manager = ResourceManager(params)
            create_result = manager.create()

            results['results'] = create_result.get('results', [])
            if create_result.get('failed'):
                results['failed'] = True
                results['msg'] = create_result.get('msg', 'Create pipeline failed')

        except FileNotFoundError as e:
            results['failed'] = True
            results['msg'] = f"Create pipeline failed — file not found: {str(e)}"
        except Exception as e:
            results['failed'] = True
            results['msg'] = f"Unexpected error during resource creation: {type(e).__name__}: {str(e)}"

        return results

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
Manage Resources — Consolidated creation pipeline for all fabric types.

Replaces the dtc/create role's per-fabric-type sub_main_*.yml files and
task files (~18 files, ~900 lines YAML) with a single data-driven plugin.

Pipeline definitions are loaded from objects/create_pipelines.yml.

Implements:
  - Recommendation #4: _vpc_peering_pipeline internal method replicating the
    original 3-step vPC creation sub-pipeline:
      1. dcnm_resource_manager (vPC domain ID allocation)
      2. dcnm_links (intra-fabric peering links) with src_fabric
      3. dcnm_vpc_pair (vPC pair configuration) with src_fabric
  - Recommendation #7: Explicit run_map_diff_run parameter instead of relying
    on cleanup cascade for diff.updated preference
  - fabric_param: Configurable fabric parameter name per step
"""

from __future__ import absolute_import, division, print_function
import json

__metaclass__ = type

from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.registry_loader import (
    RegistryLoader,
)

display = Display()


class ResourceManager:
    """
    Core creation pipeline logic.

    Iterates through the create pipeline for the given fabric type,
    checking change flag guards and data availability before calling
    the appropriate cisco.dcnm module.
    """

    def __init__(self, params, action_module, task_vars, tmp=None):
        """
        Initialize the resource manager.

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
        self.nd_version = params.get('nd_version', '')

        # Recommendation #7: Explicit diff_run parameter
        self.run_map_diff_run = params.get('run_map_diff_run', True)
        self.force_run_all = params.get('force_run_all', False)

        self.action_module = action_module
        self.task_vars = task_vars
        self.tmp = tmp

        # Load pipeline from registry
        collection_path = RegistryLoader.get_collection_path()
        registry = RegistryLoader.load(collection_path, 'create_pipelines')
        self.pipelines = registry.get('create_pipelines', {})

    def create(self):
        """
        Execute the ordered creation pipeline for the current fabric type.

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
                'msg': f"No create pipeline defined for fabric type: {self.fabric_type}",
            }

        # Filter by tags if needed
        ansible_run_tags = self.task_vars.get('ansible_run_tags', [])
        pipeline = RegistryLoader.filter_pipeline_by_tags(pipeline, ansible_run_tags)

        step_results = []

        for step in pipeline:
            resource_name = step['resource_name']
            module = step['module']
            state = step['state']
            flag_name = step.get('change_flag_guard')

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
                try:
                    method = getattr(self, module)
                    result = method(resource_name, step)
                    step_results.append({
                        'resource_name': resource_name,
                        'module': module,
                        'status': 'ok',
                        'result': result,
                    })
                    # Internal methods can signal failure
                    if isinstance(result, dict) and result.get('failed'):
                        return {
                            'results': step_results,
                            'failed': True,
                            'msg': result.get('msg', f"Internal method '{module}' failed"),
                        }
                except AttributeError:
                    step_results.append({
                        'resource_name': resource_name,
                        'module': module,
                        'status': 'failed',
                        'reason': f"Internal method '{module}' not found on ResourceManager",
                    })
                    return {
                        'results': step_results,
                        'failed': True,
                        'msg': f"Internal method '{module}' not found",
                    }
                continue

            # ── Resolve data ──────────────────────────────────────────────
            data = self._resolve_create_data(resource_name)

            if not data:
                step_results.append({
                    'resource_name': resource_name,
                    'module': module,
                    'status': 'skipped',
                    'reason': 'no data available',
                })
                continue

            # ── Determine fabric parameter name ───────────────────────────
            # dcnm_fabric embeds fabric name in config, not as a top-level param
            if module == 'dcnm_fabric':
                fabric_param = None
            # <mt> Need to review and remove as I think this stale from Claude
            else:
                module_config = step.get('module_config', {})
                fabric_param = module_config.get('fabric_param', 'fabric')

            # ── Execute NDFC module ───────────────────────────────────────
            deploy = step.get('deploy')

            display.v(
                f"CREATE [{self.fabric_name}] Executing {module} for "
                f"{resource_name} with state={state}, deploy={deploy}, "
                f"items={len(data) if isinstance(data, list) else '?'}"
            )

            result = self._execute_ndfc_module(
                module_name=f"cisco.dcnm.{module}",
                state=state,
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
                        f"Create pipeline failed at step '{resource_name}' "
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
            'msg': f"Create pipeline completed for {self.fabric_type} fabric '{self.fabric_name}'",
        }

    def _resolve_create_data(self, resource_name):
        """
        Resolve the data to send for a create step.

        Recommendation #7: Uses explicit run_map_diff_run parameter to
        gate the diff.updated preference instead of relying on cleanup cascade.

        When diff_run is active and force_run_all is False:
          - Prefers diff.updated (narrowed data set for changed items only)
          - Falls back to full data if diff.updated is not available
        When diff_run is disabled or force_run_all is True:
          - Always uses full data (complete reconciliation)

        Args:
            resource_name: Logical name of the resource.

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
        if self.run_map_diff_run and not self.force_run_all:
            diff = resource_entry.get('diff')
            if diff and isinstance(diff, dict):
                diff_data = diff.get('updated')
                if diff_data is not None:
                    data = diff_data

        return data

    def _execute_ndfc_module(self, module_name, state, config, deploy=None, fabric_param='fabric'):
        """
        Execute an NDFC Ansible module via _execute_module.

        Supports configurable fabric parameter name to handle both
        standard modules (fabric:) and dcnm_vpc_pair/dcnm_links (src_fabric:).
        When fabric_param is None, no fabric parameter is added (e.g. dcnm_fabric
        embeds the fabric name inside config).

        Args:
            module_name: Fully qualified module name.
            state: Module state parameter.
            config: Configuration data to send.
            deploy: Whether to deploy (None = omit parameter).
            fabric_param: Fabric parameter name ('fabric', 'src_fabric', or None).

        Returns:
            Module result dict.
        """
        module_args = {
            'state': state,
            'config': config,
        }
        if fabric_param is not None:
            module_args[fabric_param] = self.fabric_name
        if deploy is not None:
            module_args['deploy'] = deploy

        return self.action_module._execute_module(
            module_name=module_name,
            module_args=module_args,
            task_vars=self.task_vars,
            tmp=self.tmp,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # Internal Methods (called from pipeline via '_' prefix)
    # ══════════════════════════════════════════════════════════════════════════

# Moved into _vpc_peering_pipeline wrapper
    # def _config_save(self, resource_name, step):
    #     """
    #     Execute a config-save POST to NDFC.

    #     Matches the original block/rescue pattern: treats HTTP 500 as non-fatal
    #     since config-save can return 500 when there are no pending changes.

    #     Returns:
    #         dict with result, never fails on HTTP 500.
    #     """
    #     path = (
    #         f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control"
    #         f"/fabrics/{self.fabric_name}/config-save"
    #     )

    #     result = self.action_module._execute_module(
    #         module_name="cisco.dcnm.dcnm_rest",
    #         module_args={"method": "POST", "path": path},
    #         task_vars=self.task_vars,
    #         tmp=self.tmp,
    #     )

    #     # Treat HTTP 500 as non-fatal (matches original rescue block behavior)
    #     if result.get('failed'):
    #         return_code = None
    #         try:
    #             return_code = result.get('msg', {}).get('RETURN_CODE')
    #         except (AttributeError, TypeError):
    #             pass

    #         if return_code == 500:
    #             display.v(
    #                 f"CREATE [{self.fabric_name}] Config-save returned HTTP 500 "
    #                 f"(non-fatal — no pending changes)"
    #             )
    #             return {'failed': False, 'msg': 'Config-save HTTP 500 (non-fatal)'}

    #     return result

    def _vpc_peering_pipeline(self, resource_name, step):
        """
        Execute the vPC peering creation sub-pipeline.

        Recommendation #4: Replicates the original 3-step vPC creation from
        create/tasks/common/vpc_peering.yml:
          1. dcnm_resource_manager — Allocate vPC domain IDs
          2. dcnm_links — Create intra-fabric peering links (src_fabric)
          3. dcnm_vpc_pair — Establish vPC pairs (src_fabric, state: replaced)
          4. config-save - Config-save POST to NDFC

        Each step uses diff-aware data resolution when applicable.

        Args:
            resource_name: 'vpc_peering' (from pipeline YAML)
            step: Pipeline step dict.

        Returns:
            dict with sub-step results, 'failed' flag.
        """
        results = {}

        # Step 1: vPC Domain ID Resource Allocation
        domain_data = self._resolve_create_data('vpc_domain_id_resource')
        if domain_data:
            display.v(
                f"CREATE [{self.fabric_name}] vPC sub-pipeline step 1/3: "
                f"dcnm_resource_manager (domain IDs), items={len(domain_data)}"
            )
            result = self._execute_ndfc_module(
                module_name="cisco.dcnm.dcnm_resource_manager",
                state="merged",
                config=domain_data,
            )
            results['vpc_domain_id_resource'] = result
            if result.get('failed'):
                return {
                    'failed': True,
                    'msg': "vPC domain ID allocation failed",
                    'sub_results': results,
                }

        # Step 2: vPC Fabric Peering Links (src_fabric, no diff narrowing)
        link_entry = self.resource_data.get('vpc_fabric_peering_links', {})
        link_config = link_entry.get('data', []) if isinstance(link_entry, dict) else link_entry
        if link_config:
            display.v(
                f"CREATE [{self.fabric_name}] vPC sub-pipeline step 2/3: "
                f"dcnm_links (peering links), items={len(link_config)}"
            )
            result = self._execute_ndfc_module(
                module_name="cisco.dcnm.dcnm_links",
                state="replaced",
                config=link_config,
                fabric_param="src_fabric",
            )
            results['vpc_fabric_peering_links'] = result
            if result.get('failed'):
                return {
                    'failed': True,
                    'msg': "vPC peering links creation failed",
                    'sub_results': results,
                }

        # Step 3: vPC Pair Configuration (src_fabric, deploy=False)
        pair_data = self._resolve_create_data('vpc_peering')
        if pair_data:
            display.v(
                f"CREATE [{self.fabric_name}] vPC sub-pipeline step 3/3: "
                f"dcnm_vpc_pair (pair config), items={len(pair_data)}"
            )
            result = self._execute_ndfc_module(
                module_name="cisco.dcnm.dcnm_vpc_pair",
                state="replaced",
                config=pair_data,
                fabric_param="src_fabric",
                deploy=False,
            )
            results['vpc_peering'] = result
            if result.get('failed'):
                return {
                    'failed': True,
                    'msg': "vPC pair creation failed",
                    'sub_results': results,
                }
        # Step 4: Config-save
        path = (
            f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control"
            f"/fabrics/{self.fabric_name}/config-save"
        )

        result = self.action_module._execute_module(
            module_name="cisco.dcnm.dcnm_rest",
            module_args={"method": "POST", "path": path},
            task_vars=self.task_vars,
            tmp=self.tmp,
        )

        # Treat HTTP 500 as non-fatal (matches original rescue block behavior)
        if result.get('failed'):
            return_code = None
            try:
                return_code = result.get('msg', {}).get('RETURN_CODE')
            except (AttributeError, TypeError):
                pass

            if return_code == 500:
                display.v(
                    f"CREATE [{self.fabric_name}] Config-save returned HTTP 500 "
                    f"(non-fatal — no pending changes)"
                )
        results['config_save'] = result

        return {'failed': False, 'sub_results': results}

    def _vrfs_networks_pipeline(self, resource_name, step):
        """
        Create VRFs first, then Networks (dependency ordering).

        VRFs must exist before networks can reference them.
        Both use diff-aware data resolution when applicable.

        Returns:
            dict with sub-step results, 'failed' flag.
        """
        results = {}

        # VRFs first
        vrf_data = self._resolve_create_data('vrfs')
        if vrf_data:
            display.v(
                f"CREATE [{self.fabric_name}] VRFs+Networks sub-pipeline: "
                f"dcnm_vrf (VRFs), items={len(vrf_data)}"
            )
            result = self._execute_ndfc_module(
                module_name="cisco.dcnm.dcnm_vrf",
                state="replaced",
                config=vrf_data,
            )
            results['vrfs'] = result
            if result.get('failed'):
                return {
                    'failed': True,
                    'msg': "VRF creation failed",
                    'sub_results': results,
                }

        # Networks second
        net_data = self._resolve_create_data('networks')
        if net_data:
            display.v(
                f"CREATE [{self.fabric_name}] VRFs+Networks sub-pipeline: "
                f"dcnm_network (Networks), items={len(net_data)}"
            )
            result = self._execute_ndfc_module(
                module_name="cisco.dcnm.dcnm_network",
                state="replaced",
                config=net_data,
            )
            results['networks'] = result
            if result.get('failed'):
                return {
                    'failed': True,
                    'msg': "Network creation failed",
                    'sub_results': results,
                }

        return {'failed': False, 'sub_results': results}

    def _prepare_msite_data(self, resource_name, step):
        """
        Prepare multisite data for MSD/MCFG creation operations.

        Delegates to the existing prepare_msite_data action plugin.
        """
        return self.action_module._execute_module(
            module_name="cisco.nac_dc_vxlan.dtc.prepare_msite_data",
            module_args={
                "data_model": self.data_model,
                "parent_fabric": self.fabric_name,
                "parent_fabric_type": self.fabric_type,
                "nd_version": self.nd_version,
            },
            task_vars=self.task_vars,
            tmp=self.tmp,
        )

    def _manage_child_fabrics(self, resource_name, step):
        """
        Manage child fabric associations for MSD/MCFG creation.

        Delegates to the existing manage_child_fabrics action plugin.
        """
        return self.action_module._execute_module(
            module_name="cisco.nac_dc_vxlan.dtc.manage_child_fabrics",
            module_args={
                "data_model": self.data_model,
                "operation": "create",
            },
            task_vars=self.task_vars,
            tmp=self.tmp,
        )


class ActionModule(ActionBase):
    """
    Ansible ActionBase wrapper for manage_resources.

    Handles parameter validation, error handling, and delegation
    to the ResourceManager domain class.
    """

    REQUIRED_PARAMS = [
        'fabric_type', 'fabric_name', 'data_model', 'resource_data', 'change_flags',
    ]

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
            manager = ResourceManager(params, self, task_vars, tmp)
            result = manager.create()

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
            results['msg'] = f"Manage resources failed: {str(e)}"

        return results

# Copyright (c) 2025-2026 Cisco Systems, Inc. and its affiliates
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
Fabric Deploy Manager — Consolidated deployment for all fabric types.

Replaces the dtc/deploy role's per-fabric-type sub_main_*.yml files with a
single action plugin that resolves all fabric-type-specific parameters
internally from task_vars and data_model.

Deployment model:
  - operation 'all': Switch-level deploy — queries switch inventory, filters
    by ccStatus (NA/Pending/Out-of-Sync) and upTimeStr (non-empty), deploys
    only switches that need it. Config-save is NOT part of this workflow.
  - operation 'config_save': Standalone config-save (also used by pipeline_base
    _config_save delegation from create/remove pipelines).
  - operation 'fabric_deploy': Fabric-level deploy fallback (entire fabric).
  - operation 'switch_deploy': Standalone switch-level deploy.
  - operation 'check_sync': Check fabric sync status.

Refactored for SOLID:
  - ApiPathResolver: Strategy pattern for API path selection (OCP)
    Resolves MCFG_Child_Fabric onepath/fedproxy vs standard paths once at
    construction, eliminating repeated if/elif branching in every method.
  - ChildFabricChangeDetector: Extracts VRF/Network change merging (SRP)
    Pure data logic separated from deployment orchestration.
  - FabricDeployManager: Uses ApiPathResolver for path resolution with no
    fabric-type branching in individual methods.
"""

from __future__ import absolute_import, division, print_function


__metaclass__ = type

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase
from ansible_collections.cisco.nac_dc_vxlan.plugins.filter.version_compare import version_compare
from time import monotonic, sleep
import re

display = Display()


# ═══════════════════════════════════════════════════════════════════════════
# Multisite Fabric Types — Used for child fabric type classification
# ═══════════════════════════════════════════════════════════════════════════
MULTISITE_FABRIC_TYPES = ('MSD', 'MCFG')

# VRF/Network response variable names per multisite fabric type
# These are registered facts set by the create role's fabric-specific task files
MULTISITE_RESPONSE_VARS = {
    'MSD': {
        'vrf_result': 'manage_msd_vrf_result',
        'network_result': 'manage_msd_network_result',
    },
    'MCFG': {
        'vrf_result': 'manage_mcfg_vrf_result',
        'network_result': 'manage_mcfg_network_result',
    },
}


class ApiPathResolver:
    """Resolves API paths based on fabric type, eliminating per-method branching.

    For MCFG parent fabrics, routes through the onemanage API path.
    For MCFG child fabrics, routes through onepath (ND <=3.2.2) or fedproxy
    (ND >=4.1.1) prefixes. For all other fabric types, uses the standard
    NDFC LAN fabric REST base path.

    This is constructed once per FabricDeployManager instance, so each
    method can simply reference self.paths.<property> without branching.
    """

    ONEMANAGE_BASE = "/onemanage/appcenter/cisco/ndfc/api/v1/onemanage"

    def __init__(self, fabric_name, fabric_type, cluster_name=None, nd_version=None):
        self._fabric_type = fabric_type
        self._base = self._resolve_base(fabric_type, cluster_name, nd_version)
        self.fabric_name = fabric_name

    def _resolve_base(self, fabric_type, cluster_name, nd_version):
        base = "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest"
        if fabric_type == 'MCFG_Child_Fabric' and cluster_name:
            if version_compare(nd_version, '3.2.2', '<='):
                return f"/onepath/{cluster_name}{base}"
            elif version_compare(nd_version, '4.1.1', '>='):
                return f"/fedproxy/{cluster_name}{base}"
        return base

    @property
    def switches_by_fabric(self):
        if self._fabric_type == 'MCFG':
            return f"{self.ONEMANAGE_BASE}/fabrics/{self.fabric_name}/inventory/switchesByFabric"
        return f"{self._base}/control/fabrics/{self.fabric_name}/inventory/switchesByFabric"

    @property
    def config_save(self):
        if self._fabric_type == 'MCFG':
            return f"{self.ONEMANAGE_BASE}/fabrics/{self.fabric_name}/config-save"
        return f"{self._base}/control/fabrics/{self.fabric_name}/config-save"

    @property
    def config_deploy(self):
        if self._fabric_type == 'MCFG':
            return f"{self.ONEMANAGE_BASE}/fabrics/{self.fabric_name}/config-deploy?forceShowRun=false"
        return f"{self._base}/control/fabrics/{self.fabric_name}/config-deploy?forceShowRun=false"

    def switch_deploy(self, serial_list):
        """Path for switch-level config-deploy given a comma-separated serial number list."""
        if self._fabric_type == 'MCFG':
            return (
                f"{self.ONEMANAGE_BASE}/fabrics/{self.fabric_name}"
                f"/config-deploy/{serial_list}?forceShowRun=false"
            )
        return (
            f"{self._base}/control/fabrics/{self.fabric_name}"
            f"/config-deploy/{serial_list}?forceShowRun=false"
        )

    @property
    def fabric_history(self):
        return (
            f"{self._base}/config/delivery/deployerHistoryByFabric/"
            f"{self.fabric_name}?sort=completedTime%3ADES&limit=5"
        )


class ChildFabricChangeDetector:
    """Determines which child fabrics need deployment based on VRF/Network changes.

    Handles the merge-and-deduplicate logic for VRF and Network response data
    from the create role, producing a list of child fabrics that need deployment.

    If force_run_all is True or run_map_diff_run is False, all child fabrics
    are returned (full reconciliation). Otherwise, only child fabrics with
    detected VRF or Network changes are returned.
    """

    @staticmethod
    def detect(force_run_all, run_map_diff_run, child_fabrics, vrf_response_data, network_response_data):
        """Return list of child fabrics requiring deployment."""
        if force_run_all or not run_map_diff_run:
            return child_fabrics
        return ChildFabricChangeDetector._merge_changes(vrf_response_data, network_response_data)

    @staticmethod
    def _merge_changes(vrf_response_data, network_response_data):
        """Merge VRF and Network change data, deduplicating by fabric name."""
        vrf_changed = []
        if vrf_response_data and isinstance(vrf_response_data, dict):
            if vrf_response_data.get('child_fabrics'):
                vrf_changed = [
                    {'name': item['fabric'], 'cluster': item.get('cluster')}
                    for item in vrf_response_data['child_fabrics']
                    if item.get('changed')
                ]

        vrf_names = {f['name'] for f in vrf_changed}

        network_changed = []
        if network_response_data and isinstance(network_response_data, dict):
            if network_response_data.get('child_fabrics'):
                network_changed = [
                    {'name': item['fabric_name'], 'cluster': item.get('cluster_name')}
                    for item in network_response_data['child_fabrics']
                    if item.get('changed') and item['fabric_name'] not in vrf_names
                ]

        return vrf_changed + network_changed


class FabricDeployManager:
    """Manages fabric deployment operations via NDFC REST API.

    Uses ApiPathResolver to select the correct API paths at construction,
    so path resolution has no fabric-type branching in individual methods.

    Supports both fabric-level deployment (fabric_deploy) and switch-level
    deployment (get_deployable_switches + switch_deploy) which filters by
    ccStatus and upTimeStr to deploy only switches that need it.
    """

    def __init__(self, params):

        # Fabric Parameters
        self.fabric_name = params['fabric_name']
        self.fabric_type = params['fabric_type']

        # Module Execution Parameters
        self.task_vars = params['task_vars']
        self.tmp = params['tmp']
        self.action_module = params['action_module']
        self.module_name = "cisco.dcnm.dcnm_rest"

        # API Path Resolution (Strategy Pattern)
        self.paths = ApiPathResolver(
            fabric_name=self.fabric_name,
            fabric_type=self.fabric_type,
            cluster_name=params.get('cluster_name'),
            nd_version=params.get('nd_major_minor_patch'),
        )

        # Fabric State Booleans
        self.fabric_in_sync = True
        self.fabric_save_succeeded = True
        self.fabric_deploy_succeeded = True

        # Fabric History
        self.fabric_history = []

    def fabric_check_sync(self):
        """Check if the fabric is in sync."""
        step_start = monotonic()
        display.display(
            f"\n{'─' * display.columns}\n"
            f"DEPLOY [{self.fabric_name}] check_sync\n"
            f"{'─' * display.columns}",
            color='dark gray',
        )

        self.fabric_in_sync = True
        response = self._send_request("GET", self.paths.switches_by_fabric)

        # For non-Multisite fabrics, retry up to 5 times if out-of-sync
        # Exclude Multisite parent fabrics (MSD or MCFG) as they are dependent on child fabrics being in sync
        if self.fabric_type not in MULTISITE_FABRIC_TYPES:
            for attempt in range(5):
                self._fabric_check_sync_helper(response)
                if self.fabric_in_sync:
                    break
                if (attempt + 1) == 5 and not self.fabric_in_sync:
                    break
                else:
                    elapsed = monotonic() - step_start
                    display.display(
                        f"DEPLOY [{self.fabric_name}] "
                        f"check_sync → out of sync, retry {attempt + 1}/5 [{elapsed:.1f}s]",
                        color='yellow',
                    )
                    sleep(2)
                    self.fabric_in_sync = True
                    response = self._send_request("GET", self.paths.switches_by_fabric)

        elapsed = monotonic() - step_start
        if self.fabric_in_sync:
            display.display(
                f"DEPLOY [{self.fabric_name}] "
                f"check_sync → ok (in_sync=True) [{elapsed:.1f}s]",
                color='green',
            )
        else:
            display.display(
                f"DEPLOY [{self.fabric_name}] "
                f"check_sync → warning (in_sync=False) [{elapsed:.1f}s]",
                color='yellow',
            )

    def _fabric_check_sync_helper(self, response):
        if response.get('DATA'):
            for switch in response['DATA']:
                # Devices that are not managable (example: pre-provisioned devices) should be
                # skipped in this check
                if str(switch['managable']) == 'True' and switch['ccStatus'] == 'Out-of-Sync':
                    self.fabric_in_sync = False
                    break

    def fabric_config_save(self):
        """Trigger a config-save on the fabric."""
        step_start = monotonic()
        display.display(
            f"\n{'─' * display.columns}\n"
            f"DEPLOY [{self.fabric_name}] config_save\n"
            f"{'─' * display.columns}",
            color='dark gray',
        )

        response = self._send_request("POST", self.paths.config_save)
        elapsed = monotonic() - step_start
        if response.get('RETURN_CODE') != 200:
            self.fabric_save_succeeded = False
            display.display(
                f"DEPLOY [{self.fabric_name}] "
                f"config_save → failed [{elapsed:.1f}s]",
                color='red',
            )
            display.v(f"DEPLOY [{self.fabric_name}] config_save failure detail: {response}")
        else:
            display.display(
                f"DEPLOY [{self.fabric_name}] "
                f"config_save → ok [{elapsed:.1f}s]",
                color='green',
            )

    def fabric_deploy(self):
        """Deploy the fabric configuration (fabric-level)."""
        step_start = monotonic()
        display.display(
            f"\n{'─' * display.columns}\n"
            f"DEPLOY [{self.fabric_name}] fabric_deploy\n"
            f"{'─' * display.columns}",
            color='dark gray',
        )

        response = self._send_request("POST", self.paths.config_deploy)
        elapsed = monotonic() - step_start
        if response.get('RETURN_CODE') != 200:
            self.fabric_deploy_succeeded = False
            display.display(
                f"DEPLOY [{self.fabric_name}] "
                f"fabric_deploy → failed [{elapsed:.1f}s]",
                color='red',
            )
            display.v(f"DEPLOY [{self.fabric_name}] fabric_deploy failure detail: {response}")
        else:
            display.display(
                f"DEPLOY [{self.fabric_name}] "
                f"fabric_deploy → ok [{elapsed:.1f}s]",
                color='green',
            )

    def get_deployable_switches(self):
        """Query switch inventory and return serial numbers needing deployment.

        A switch needs deployment when both conditions are true:
          - ccStatus is one of: NA, Pending, Out-of-Sync
          - upTimeStr is not an empty string (switch is up and reachable)
        """
        DEPLOYABLE_CC_STATUSES = ('NA', 'Pending', 'Out-of-Sync')

        step_start = monotonic()
        display.display(
            f"\n{'─' * display.columns}\n"
            f"DEPLOY [{self.fabric_name}] get_deployable_switches\n"
            f"{'─' * display.columns}",
            color='dark gray',
        )

        response = self._send_request("GET", self.paths.switches_by_fabric)
        switches = response.get('DATA', [])

        deployable_serials = []
        for switch in switches:
            cc_status = switch.get('ccStatus', '')
            up_time_str = switch.get('upTimeStr', '')
            serial = switch.get('serialNumber', '')
            hostname = switch.get('hostName', switch.get('logicalName', 'unknown'))

            if cc_status in DEPLOYABLE_CC_STATUSES and up_time_str:
                display.v(
                    f"  Switch {hostname} ({serial}): ccStatus={cc_status}, "
                    f"upTimeStr={up_time_str} — needs deployment"
                )
                deployable_serials.append(serial)
            else:
                display.v(
                    f"  Switch {hostname} ({serial}): ccStatus={cc_status}, "
                    f"upTimeStr={up_time_str} — skipping"
                )

        elapsed = monotonic() - step_start
        if deployable_serials:
            display.display(
                f"DEPLOY [{self.fabric_name}] "
                f"get_deployable_switches → ok "
                f"(changed={len(deployable_serials)}/{len(switches)}) [{elapsed:.1f}s]",
                color='yellow',
            )
        else:
            display.display(
                f"DEPLOY [{self.fabric_name}] "
                f"get_deployable_switches → ok "
                f"(changed=0/{len(switches)}) [{elapsed:.1f}s]",
                color='green',
            )
        return deployable_serials

    def switch_deploy(self, serial_numbers):
        """Deploy configuration to specific switches by serial number list."""
        step_start = monotonic()
        display.display(
            f"\n{'─' * display.columns}\n"
            f"DEPLOY [{self.fabric_name}] switch_deploy ({len(serial_numbers)} switches)\n"
            f"{'─' * display.columns}",
            color='dark gray',
        )

        if not serial_numbers:
            elapsed = monotonic() - step_start
            display.display(
                f"DEPLOY [{self.fabric_name}] "
                f"switch_deploy → skipped (no switches) [{elapsed:.1f}s]",
                color='cyan',
            )
            return

        serial_list = ','.join(serial_numbers)
        response = self._send_request("POST", self.paths.switch_deploy(serial_list))
        elapsed = monotonic() - step_start
        if response.get('RETURN_CODE') != 200:
            self.fabric_deploy_succeeded = False
            display.display(
                f"DEPLOY [{self.fabric_name}] "
                f"switch_deploy → failed [{elapsed:.1f}s]",
                color='red',
            )
            display.v(f"DEPLOY [{self.fabric_name}] switch_deploy failure detail: {response}")
        else:
            display.display(
                f"DEPLOY [{self.fabric_name}] "
                f"switch_deploy → ok (changed={len(serial_numbers)}) [{elapsed:.1f}s]",
                color='yellow',
            )

    def fabric_history_get(self):
        """Retrieve fabric deployment history."""
        step_start = monotonic()
        display.display(
            f"\n{'─' * display.columns}\n"
            f"DEPLOY [{self.fabric_name}] fabric_history_get\n"
            f"{'─' * display.columns}",
            color='dark gray',
        )

        response = self._send_request("GET", self.paths.fabric_history)
        elapsed = monotonic() - step_start
        if response.get('RETURN_CODE') != 200:
            display.display(
                f"DEPLOY [{self.fabric_name}] "
                f"fabric_history_get → failed [{elapsed:.1f}s]",
                color='red',
            )
            display.v(f"DEPLOY [{self.fabric_name}] fabric_history_get failure detail: {response}")
        else:
            display.display(
                f"DEPLOY [{self.fabric_name}] "
                f"fabric_history_get → ok [{elapsed:.1f}s]",
                color='green',
            )

        # Get last 2 history entries
        self.fabric_history = response.get('DATA', [])[0:2]

    def _send_request(self, method, path, data=None):
        """Helper method to send REST API requests."""

        module_args = {
            "method": method,
            "path": path,
        }
        if data:
            module_args["data"] = data

        response = self.action_module._execute_module(
            module_name=self.module_name,
            module_args=module_args,
            task_vars=self.task_vars,
            tmp=self.tmp
        )
        if 'response' in response.keys():
            response = response['response']
        if 'msg' in response.keys():
            response = response['msg']
        return response


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False

        params = {}
        # Module Execution Context Parameters
        params['task_vars'] = task_vars
        params['tmp'] = tmp
        params['action_module'] = self

        params['fabric_name'] = self._task.args["fabric_name"]
        params['fabric_type'] = self._task.args["fabric_type"]

        # Operations supported include 'all', 'config_save', 'fabric_deploy', 'switch_deploy', 'check_sync'
        params['operation'] = self._task.args.get("operation")

        # Manage Deployment For Multisite (MSD or MCFG) Parent or Standalone Fabric
        results = self.manage_fabrics(results, params)
        if results.get('failed'):
            return results

        if params['fabric_type'] in MULTISITE_FABRIC_TYPES:
            # Manage Deployment For Child Fabrics if Multisite (MSD or MCFG)
            # Child fabrics are only deployed if there are VRF or Network changes
            # detected. If force_run_all is True or run_map_diff_run is False,
            # all child fabrics will be deployed regardless of change detection.

            # Resolve multisite parameters from data_model and task_vars
            results = self._resolve_and_process_child_fabrics(results, params)
            if results.get('failed'):
                return results

        return results

    def _resolve_and_process_child_fabrics(self, results, params):
        """Resolve multisite parameters from data_model/task_vars and process child fabrics."""
        fabric_type = params['fabric_type']

        # Resolve data_model from task args (consolidated entry point)
        # or fall back to individual args (legacy sub_main compatibility)
        data_model = self._task.args.get("data_model")

        if data_model:
            # Consolidated path: resolve from data_model
            child_fabrics = data_model.get('vxlan', {}).get('multisite', {}).get('child_fabrics', [])
        else:
            # Legacy path: passed directly as task arg
            child_fabrics = self._task.args.get("data_model_child_fabrics", [])

        if not child_fabrics:
            return results

        # Resolve VRF/Network response data from task_vars (registered facts from create role)
        response_vars = MULTISITE_RESPONSE_VARS.get(fabric_type, {})
        vrf_response_data = params['task_vars'].get(response_vars.get('vrf_result', ''), [])
        network_response_data = params['task_vars'].get(response_vars.get('network_result', ''), [])

        # Resolve force_run_all and run_map_diff_run
        force_run_all = self._task.args.get("force_run_all", False)
        run_map_diff_run = self._task.args.get("run_map_diff_run", True)

        # MCFG requires ND version for API path routing
        nd_major_minor_patch = None
        if fabric_type == 'MCFG':
            nd_version = self._task.args.get("nd_version", "")
            match = re.match(r'^(\d+\.\d+\.\d+)([a-z])?$', nd_version)
            if match:
                nd_major_minor_patch = match.group(1)

            if nd_major_minor_patch is None:
                results['failed'] = True
                results['msg'] = "Missing or invalid 'nd_version' parameter required for MCFG fabric deployment"
                return results

        params['nd_major_minor_patch'] = nd_major_minor_patch

        # Detect which child fabrics need deployment
        changed_fabrics = ChildFabricChangeDetector.detect(
            force_run_all=force_run_all,
            run_map_diff_run=run_map_diff_run,
            child_fabrics=child_fabrics,
            vrf_response_data=vrf_response_data,
            network_response_data=network_response_data,
        )

        # Deploy changed child fabrics
        if changed_fabrics:
            child_fabric_type = f"{fabric_type}_Child_Fabric"

            for changed_fabric in changed_fabrics:
                params['fabric_name'] = changed_fabric['name']
                params['fabric_type'] = child_fabric_type
                params['cluster_name'] = changed_fabric.get('cluster', None)
                display.display(
                    f"\n{'─' * display.columns}\n"
                    f"DEPLOY [{params['fabric_name']}] "
                    f"child_fabric (cluster={params['cluster_name']})\n"
                    f"{'─' * display.columns}",
                    color='dark gray',
                )

                results = self.manage_fabrics(results, params)
                if results.get('failed'):
                    return results

        return results

    def manage_fabrics(self, results, params):
        """Manage fabric deployments based on operation parameter."""
        fabric_name = params['fabric_name']
        operation = params['operation']

        for key in ['fabric_type', 'fabric_name', 'operation']:
            if params[key] is None:
                results['failed'] = True
                results['msg'] = f"Missing required parameter '{key}'"
                return results

        if operation not in ['all', 'config_save', 'fabric_deploy', 'switch_deploy', 'check_sync']:
            results['failed'] = True
            results['msg'] = "Parameter 'operation' must be one of: [all, config_save, fabric_deploy, switch_deploy, check_sync]"
            return results

        workflow_start = monotonic()
        display.display(
            f"\n{'═' * display.columns}\n"
            f"DEPLOY [{fabric_name}] "
            f"Workflow start — operation: {operation}\n"
            f"{'═' * display.columns}",
            color='dark gray',
        )

        fabric_manager = FabricDeployManager(params)

        # Workflows
        if operation == 'all':
            # Switch-level deploy: query switches, deploy only those that need it
            # Config-save is NOT part of this workflow — it is handled by the
            # create pipeline's _config_save steps at the appropriate points.
            deployable = fabric_manager.get_deployable_switches()
            if deployable:
                fabric_manager.switch_deploy(deployable)
                fabric_manager.fabric_check_sync()

                # For non-Multisite fabrics, retry if still out-of-sync
                if not fabric_manager.fabric_in_sync and params['fabric_type'] not in MULTISITE_FABRIC_TYPES:
                    fabric_manager.fabric_history_get()
                    display.display(
                        f"DEPLOY [{fabric_name}] "
                        f"out of sync after initial deployment, retrying",
                        color='yellow',
                    )
                    deployable = fabric_manager.get_deployable_switches()
                    if deployable:
                        fabric_manager.switch_deploy(deployable)
                        fabric_manager.fabric_check_sync()

                if not fabric_manager.fabric_in_sync and params['fabric_type'] not in MULTISITE_FABRIC_TYPES:
                    fabric_manager.fabric_history_get()
                    results['msg'] = f"Fabric {fabric_manager.fabric_name} is out of sync after deployment."
                    results['fabric_history'] = fabric_manager.fabric_history
                    results['failed'] = True
            else:
                display.display(
                    f"DEPLOY [{fabric_name}] "
                    f"all → skipped (no switches need deployment)",
                    color='cyan',
                )

        if operation == 'config_save':
            fabric_manager.fabric_config_save()
            if not fabric_manager.fabric_save_succeeded:
                results['failed'] = True

        if operation == 'fabric_deploy':
            fabric_manager.fabric_deploy()
            if not fabric_manager.fabric_deploy_succeeded:
                results['failed'] = True

        if operation == 'switch_deploy':
            deployable = fabric_manager.get_deployable_switches()
            if deployable:
                fabric_manager.switch_deploy(deployable)
            else:
                display.display(
                    f"DEPLOY [{fabric_name}] "
                    f"switch_deploy → skipped (no switches need deployment)",
                    color='cyan',
                )
            if not fabric_manager.fabric_deploy_succeeded:
                results['failed'] = True

        if operation == 'check_sync':
            fabric_manager.fabric_check_sync()
            if not fabric_manager.fabric_in_sync:
                fabric_manager.fabric_history_get()
                results['msg'] = f"Fabric {fabric_manager.fabric_name} is out of sync."
                results['fabric_history'] = fabric_manager.fabric_history
                results['failed'] = True

        workflow_elapsed = monotonic() - workflow_start
        status_color = 'red' if results.get('failed') else 'dark gray'
        display.display(
            f"\n{'═' * display.columns}\n"
            f"DEPLOY [{fabric_name}] "
            f"Workflow complete — operation: {operation} [{workflow_elapsed:.1f}s]\n"
            f"{'═' * display.columns}",
            color=status_color,
        )

        return results

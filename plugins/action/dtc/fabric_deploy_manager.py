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

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase
import inspect
from time import sleep

display = Display()


class FabricDeployManager:
    """Manages fabric deployment tasks."""

    def __init__(self, params):
        self.class_name = self.__class__.__name__
        method_name = inspect.stack()[0][3]

        # Fabric Parameters
        self.fabric_name = params['fabric_name']
        self.fabric_type = params['fabric_type']

        # Module Execution Parameters
        self.task_vars = params['task_vars']
        self.tmp = params['tmp']
        self.action_module = params['action_module']
        self.module_name = "cisco.dcnm.dcnm_rest"

        # Module API Paths
        base_path = "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest"
        self.api_paths = {
            "get_switches_by_fabric": f"{base_path}/control/fabrics/{self.fabric_name}/inventory/switchesByFabric",
            "config_save": f"{base_path}/control/fabrics/{self.fabric_name}/config-save",
            "config_deploy": f"{base_path}/control/fabrics/{self.fabric_name}/config-deploy?forceShowRun=false",
            "fabric_history": f"{base_path}/config/delivery/deployerHistoryByFabric/{self.fabric_name}?sort=completedTime%3ADES&limit=5",
        }

        # Fabric State Booleans
        self.fabric_in_sync = True
        self.fabric_save_succeeded = True
        self.fabric_deploy_succeeded = True

        # Fabric History
        self.fabric_history = []

    def fabric_check_sync(self):
        """Check if the fabric is in sync."""
        method_name = inspect.stack()[0][3]
        display.banner(f"{self.class_name}.{method_name}() Fabric: ({self.fabric_name}) Type: ({self.fabric_type})")

        self.fabric_in_sync = True
        response = self._send_request("GET", self.api_paths["get_switches_by_fabric"])

        # For non-Multisite fabrics, retry up to 5 times if out-of-sync
        # Exclude Multisite parent fabrics (MSD or MCFG) as they are dependent on child fabrics being in sync
        if self.fabric_type not in ['MSD', 'MCFG']:
            for attempt in range(5):
                self._fabric_check_sync_helper(response)
                if self.fabric_in_sync:
                    break
                if (attempt + 1) == 5 and not self.fabric_in_sync:
                    break
                else:
                    display.warning(f"Fabric {self.fabric_name} is out of sync. Attempt {attempt + 1}/5. Sleeping 2 seconds before retry.")
                    sleep(2)
                    self.fabric_in_sync = True
                    response = self._send_request("GET", self.api_paths["get_switches_by_fabric"])

        display.banner(f">>>> Fabric: ({self.fabric_name}) Type: ({self.fabric_type}) in sync: {self.fabric_in_sync}")
        display.banner(">>>>")

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
        method_name = inspect.stack()[0][3]
        display.banner(f"{self.class_name}.{method_name}() Fabric: ({self.fabric_name}) Type: ({self.fabric_type})")

        response = self._send_request("POST", self.api_paths["config_save"])
        if response.get('RETURN_CODE') == 200:
            pass
        else:
            self.fabric_save_succeeded = False
            display.warning(f">>>> Failed for Fabric {self.fabric_name}: {response}")

    def fabric_deploy(self):
        """Deploy the fabric configuration."""
        method_name = inspect.stack()[0][3]
        display.banner(f"{self.class_name}.{method_name}() Fabric: ({self.fabric_name}) Type: ({self.fabric_type})")

        response = self._send_request("POST", self.api_paths["config_deploy"])
        if response.get('RETURN_CODE') == 200:
            pass
        else:
            self.fabric_deploy_succeeded = False
            display.warning(f">>>> Failed for Fabric {self.fabric_name}: {response}")

    def fabric_history_get(self):
        """Retrieve fabric deployment history."""
        method_name = inspect.stack()[0][3]
        display.banner(f"{self.class_name}.{method_name}() Fabric: ({self.fabric_name}) Type: ({self.fabric_type})")

        response = self._send_request("GET", self.api_paths["fabric_history"])
        if response.get('RETURN_CODE') == 200:
            pass
        else:
            display.warning(f">>>> Failed for Fabric {self.fabric_name}: {response}")

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

        # Operations supported include 'all', 'config_save', 'config_deploy', 'check_sync'
        params['operation'] = self._task.args.get("operation")

        # Manage Deployment For Multisite (MSD or MCFG) Parent or Standalone Fabric
        results = self.manage_fabrics(results, params)
        if results.get('failed'):
            return results

        if params['fabric_type'] in ['MSD', 'MCFG']:
            # Manage Deployment For Child Fabrics if Multisite (MSD or MCFG)
            # Child Fabrics are only deployed if there are VRF or Network changes detected by passing in the response data from those tasks
            # Additionally, if force_run_all is set to True or run_map_diff_run is set to False, all child fabrics will be deployed regardless of change detection
            params['force_run_all'] = self._task.args.get("force_run_all", False)
            params['run_map_diff_run'] = self._task.args.get("run_map_diff_run", True)
            params['dm_child_fabrics'] = self._task.args.get("data_model_child_fabrics")
            params['vrf_response_data'] = self._task.args.get("vrf_response_data", False)
            params['network_response_data'] = self._task.args.get("network_response_data", False)

            results = self.process_child_fabric_changes(results, params)
            if results.get('failed'):
                return results

        return results

    def manage_fabrics(self, results, params):
        """Manage fabric deployments based on operation parameter."""

        for key in ['fabric_type', 'fabric_name', 'operation']:
            if params[key] is None:
                results['failed'] = True
                results['msg'] = f"Missing required parameter '{key}'"
                return results

        if params['operation'] not in ['all', 'config_save', 'config_deploy', 'check_sync']:
            results['failed'] = True
            results['msg'] = "Parameter 'operation' must be one of: [all, config_save, config_deploy, check_sync]"
            return results

        fabric_manager = FabricDeployManager(params)

        # Workflows
        if params['operation'] in ['all']:
            fabric_manager.fabric_config_save()
            fabric_manager.fabric_deploy()
            fabric_manager.fabric_check_sync()

            # For non-Multisite fabrics, check fabric history and retry deployment if out-of-sync
            # Multisite parent fabrics (MSD or MCFG) are excluded as they are dependent on child fabrics being in sync
            if not fabric_manager.fabric_in_sync and params['fabric_type'] not in ['MSD', 'MCFG']:
                # If the fabric is out of sync after deployment try one more time before giving up
                fabric_manager.fabric_history_get()
                display.warning(fabric_manager.fabric_history)
                display.warning("Fabric is out of sync after initial deployment. Attempting one more deployment.")
                fabric_manager.fabric_config_save()
                fabric_manager.fabric_deploy()
                fabric_manager.fabric_check_sync()

            if not fabric_manager.fabric_in_sync and params['fabric_type'] not in ['MSD', 'MCFG']:
                fabric_manager.fabric_history_get()
                results['msg'] = f"Fabric {fabric_manager.fabric_name} is out of sync after deployment."
                results['fabric_history'] = fabric_manager.fabric_history
                results['failed'] = True

        if params['operation'] in ['config_save']:
            fabric_manager.fabric_config_save()
            if not fabric_manager.fabric_save_succeeded:
                results['failed'] = True

        if params['operation'] in ['config_deploy']:
            fabric_manager.fabric_deploy()
            if not fabric_manager.fabric_deploy_succeeded:
                results['failed'] = True

        if params['operation'] in ['check_sync']:
            fabric_manager.fabric_check_sync()
            if not fabric_manager.fabric_in_sync:
                fabric_manager.fabric_history_get()
                results['msg'] = f"Fabric {fabric_manager.fabric_name} is out of sync."
                results['fabric_history'] = fabric_manager.fabric_history
                results['failed'] = True

        return results

    def process_child_fabric_changes(self, results, params):
        """Process child fabric changes for Multisite (MSD or MCFG) deployments."""

        for key in ['force_run_all', 'run_map_diff_run', 'dm_child_fabrics', 'vrf_response_data', 'network_response_data']:
            if params[key] is None:
                results['failed'] = True
                results['msg'] = f"Missing required parameter '{key}'"
                return results

        changed_fabrics = []
        if params['force_run_all'] or not params['run_map_diff_run']:
            # Process all child fabrics
            changed_fabrics = params['dm_child_fabrics']
        else:
            # Process child fabric changes for VRFs and Networks
            changed_fabrics = self._process_child_fabric_changes(params)

        # Manage child fabric deployments based on force_run_all/run_map_diff_run or detected changes in VRFs or Networks
        if changed_fabrics:
            params['fabric_type'] = "Multi-Site_Child_Fabric"
            for changed_fabric in changed_fabrics:
                params['fabric_name'] = changed_fabric['name']
                results = self.manage_fabrics(results, params)
                if results.get('failed'):
                    return results

        return results

    def _process_child_fabric_changes(self, params):
        """Helper for processing child fabric changes for Multisite (MSD or MCFG) deployments."""
        vrf_response_data = params['vrf_response_data']
        network_response_data = params['network_response_data']

        vrf_changed_fabrics = []
        network_changed_fabrics = []

        # Process VRF Changes
        if vrf_response_data:
            if vrf_response_data.get('child_fabrics'):
                child_fabric_vrf_data = vrf_response_data['child_fabrics']

                # As part of VRF changes detected, get list of changed fabrics
                vrf_changed_fabrics = [
                    {
                        'name': item['fabric'],
                        'cluster': item.get('cluster')
                    }
                    for item in child_fabric_vrf_data
                    if item.get('changed')
                ]

        # Process Network Changes
        if network_response_data:
            if network_response_data.get('child_fabrics'):
                child_fabric_network_data = network_response_data['child_fabrics']

                # As part of Network changes detected, exclude fabrics that have already been marked as changed due to VRF changes
                network_changed_fabrics = [
                    {
                        'name': item['fabric_name'],
                        'cluster': item.get('cluster_name')
                    }
                    for item in child_fabric_network_data
                    if item.get('changed') and item['fabric_name'] not in vrf_changed_fabrics
                ]

        merged_fabric_changes = vrf_changed_fabrics + [
            network_changed_fabric
            for network_changed_fabric in network_changed_fabrics
            if network_changed_fabric['name'] not in {
                network_changed_fabric['name'] for network_changed_fabric in vrf_changed_fabrics
            }
        ]

        return merged_fabric_changes

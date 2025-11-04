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
        params['operation'] = self._task.args.get("operation")

        # Manage Deployment For Multisite or Standalone Fabric
        results = self.manage_fabrics(results, params)
        if results.get('failed'):
            return results

        params['child_fabric_vrf_data'] = self._task.args.get("child_fabric_vrf_data", {})
        import epdb ; epdb.set_trace()

        return results
        # for key in ['fabric_type', 'fabric_name', 'operation']:
        #     if params[key] is None:
        #         results['failed'] = True
        #         results['msg'] = f"Missing required parameter '{key}'"
        #         return results

        # if params['operation'] not in ['all', 'config_save', 'config_deploy', 'check_sync']:
        #     results['failed'] = True
        #     results['msg'] = "Parameter 'operation' must be one of: [all, config_save, config_deploy, check_sync]"
        #     return results

        # fabric_manager = FabricDeployManager(params)

        # # Workflows
        # if params['operation'] in ['all']:
        #     fabric_manager.fabric_config_save()
        #     fabric_manager.fabric_deploy()
        #     fabric_manager.fabric_check_sync()

        #     if not fabric_manager.fabric_in_sync and params['fabric_type'] != 'MSD':
        #         # If the fabric is out of sync after deployment try one more time before giving up
        #         fabric_manager.fabric_history_get()
        #         display.warning(fabric_manager.fabric_history)
        #         display.warning("Fabric is out of sync after initial deployment. Attempting one more deployment.")
        #         fabric_manager.fabric_config_save()
        #         fabric_manager.fabric_deploy()
        #         fabric_manager.fabric_check_sync()

        #     if not fabric_manager.fabric_in_sync and params['fabric_type'] != 'MSD':
        #         fabric_manager.fabric_history_get()
        #         results['msg'] = f"Fabric {fabric_manager.fabric_name} is out of sync after deployment."
        #         results['fabric_history'] = fabric_manager.fabric_history
        #         results['failed'] = True

        # if params['operation'] in ['config_save']:
        #     fabric_manager.fabric_config_save()
        #     if not fabric_manager.fabric_save_succeeded:
        #         results['failed'] = True

        # if params['operation'] in ['config_deploy']:
        #     fabric_manager.fabric_deploy()
        #     if not fabric_manager.fabric_deploy_succeeded:
        #         results['failed'] = True

        # if params['operation'] in ['check_sync']:
        #     fabric_manager.fabric_check_sync()
        #     if not fabric_manager.fabric_in_sync:
        #         fabric_manager.fabric_history_get()
        #         results['msg'] = f"Fabric {fabric_manager.fabric_name} is out of sync."
        #         results['fabric_history'] = fabric_manager.fabric_history
        #         results['failed'] = True


    def manage_fabrics(self, results, params):

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

            if not fabric_manager.fabric_in_sync and params['fabric_type'] != 'MSD':
                # If the fabric is out of sync after deployment try one more time before giving up
                fabric_manager.fabric_history_get()
                display.warning(fabric_manager.fabric_history)
                display.warning("Fabric is out of sync after initial deployment. Attempting one more deployment.")
                fabric_manager.fabric_config_save()
                fabric_manager.fabric_deploy()
                fabric_manager.fabric_check_sync()

            if not fabric_manager.fabric_in_sync and params['fabric_type'] != 'MSD':
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
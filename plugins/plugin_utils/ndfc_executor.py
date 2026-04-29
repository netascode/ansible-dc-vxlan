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
NDFC Module Executor — Shared module execution service for DTC pipeline plugins.

Encapsulates all NDFC module execution logic including direct module calls,
action plugin routing for modules with companion action plugins (dcnm_vrf,
dcnm_network), REST API calls, and arbitrary plugin execution.

Used by both manage_resources (create pipeline) and remove_resources (remove
pipeline) via constructor injection.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.utils.display import Display

display = Display()


class NdfcModuleExecutor:
    """
    Encapsulates all NDFC module execution logic.

    Handles direct module execution and action plugin routing
    for modules with companion action plugins (dcnm_vrf, dcnm_network).
    """

    # Modules with companion action plugins that must be invoked to replicate
    # native Ansible task execution (e.g. fabric discovery, metadata injection).
    MODULES_WITH_ACTION_PLUGINS = frozenset({
        'cisco.dcnm.dcnm_vrf',
        'cisco.dcnm.dcnm_network',
    })

    def __init__(self, action_module, task_vars, tmp=None):
        """
        Initialize the executor.

        Args:
            action_module: Reference to the ActionModule instance for _execute_module.
            task_vars: Ansible task variables.
            tmp: Temporary directory (Ansible internal).
        """
        self.action_module = action_module
        self.task_vars = task_vars
        self.tmp = tmp

    def execute(self, module_name, state, config, fabric_name, save=None, deploy=None, fabric_param='fabric', skip_validation=None):
        """
        Execute an NDFC Ansible module.

        Supports configurable fabric parameter name to handle both
        standard modules (fabric:) and dcnm_vpc_pair/dcnm_links (src_fabric:).
        When fabric_param is None, no fabric parameter is added (e.g. dcnm_fabric
        embeds the fabric name inside config).

        For modules with companion action plugins (dcnm_vrf, dcnm_network),
        delegates to the action plugin via action_loader so execution matches
        native Ansible task behavior.

        Args:
            module_name: Fully qualified module name (e.g. 'cisco.dcnm.dcnm_vrf').
            state: Module state parameter.
            config: Configuration data to send.
            fabric_name: Fabric name for fabric parameter.
            deploy: Whether to deploy (None = omit parameter).
            fabric_param: Fabric parameter name ('fabric', 'src_fabric', or None).

        Returns:
            Module result dict.
        """
        # Strip omit placeholders from config before passing to modules.
        # Ansible's TaskExecutor calls remove_omit() on module_args for native
        # YAML tasks, but our programmatic invocation bypasses that path.
        config = self._remove_omit_placeholders(config)

        module_args = {
            'state': state,
            'config': config,
        }
        if fabric_param is not None:
            module_args[fabric_param] = fabric_name
        if save is not None:
            module_args['save'] = save
        if deploy is not None:
            module_args['deploy'] = deploy

        if module_name == 'cisco.dcnm.dcnm_policy':
            module_args['use_desc_as_key'] = True

        if skip_validation is not None:
            module_args['skip_validation'] = skip_validation
        
        if module_name in self.MODULES_WITH_ACTION_PLUGINS:
            return self._execute_via_action_plugin(module_name, module_args)

        return self.action_module._execute_module(
            module_name=module_name,
            module_args=module_args,
            task_vars=self.task_vars,
            tmp=self.tmp,
        )

    def execute_rest(self, method, path, json_data=None):
        """
        Execute a dcnm_rest API call.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: NDFC API path.
            json_data: Optional JSON string for request body (POST/PUT).

        Returns:
            Module result dict.
        """
        module_args = {"method": method, "path": path}
        if json_data is not None:
            module_args["json_data"] = json_data
        return self.action_module._execute_module(
            module_name="cisco.dcnm.dcnm_rest",
            module_args=module_args,
            task_vars=self.task_vars,
            tmp=self.tmp,
        )

    def execute_plugin(self, module_name, module_args):
        """
        Execute an arbitrary action plugin by FQCN.

        Delegates to _execute_via_action_plugin which handles action_loader
        dispatch, task state save/restore, and plugin invocation.

        Args:
            module_name: Fully qualified action plugin name
                         (e.g. 'cisco.nac_dc_vxlan.dtc.prepare_msite_data').
            module_args: Dict of plugin arguments.

        Returns:
            Plugin result dict.
        """
        return self._execute_via_action_plugin(module_name, module_args)

    @staticmethod
    def _remove_omit_placeholders(data):
        """Recursively remove dict entries whose values contain '__omit_place_holder__'.

        Replicates the behaviour of Ansible's TaskExecutor.remove_omit() which
        strips omit sentinel values from module_args before module invocation.
        When modules are called programmatically via _execute_via_action_plugin,
        that native stripping is bypassed — this method fills the gap.
        """
        if isinstance(data, list):
            return [NdfcModuleExecutor._remove_omit_placeholders(item) for item in data]
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                if isinstance(value, str) and '__omit_place_holder__' in value:
                    continue
                cleaned[key] = NdfcModuleExecutor._remove_omit_placeholders(value)
            return cleaned
        return data

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

            if action_plugin is None:
                return {
                    'failed': True,
                    'msg': f"Action plugin '{module_name}' not found via action_loader",
                }

            return action_plugin.run(task_vars=self.task_vars, tmp=self.tmp)
        finally:
            self.action_module._task.args = original_args
            self.action_module._task.action = original_action

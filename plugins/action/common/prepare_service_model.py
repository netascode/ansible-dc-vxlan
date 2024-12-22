# Copyright (c) 2024 Cisco Systems, Inc. and its affiliates
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

import importlib
import os
import pathlib
import copy

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        # self._supports_async = True
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False
        results['msg'] = None
        results['model_extended'] = None

        # Get Data from Ansible Task
        ihn = self._task.args['inventory_hostname']
        hvs = self._task.args['hostvars']
        tp = self._task.args['templates_path']
        default_values = self._task.args['default_values']

        # sm_data contains the golden untouched model data
        sm_data = self._task.args['model_data']
        # results['model_extended'] contains the data that can be extended by the plugins
        results['model_extended'] = copy.deepcopy(sm_data)

        full_plugin_path = "ansible_collections.cisco.nac_dc_vxlan.plugins.action.common.prepare_plugins"
        glob_plugin_path = os.path.dirname(__file__) + "/prepare_plugins"
        plugin_prefix = "prep*.py"

        prepare_libs = set(x.stem for x in pathlib.Path.glob(pathlib.Path(glob_plugin_path), plugin_prefix))
        dict_of_plugins = {}
        for lib in prepare_libs:
            plugin_name = f"{full_plugin_path}.{lib}"
            plugin_module = importlib.import_module(plugin_name, ".")
            dict_of_plugins[lib] = plugin_module

        plugin_keys = list(dict_of_plugins)
        plugin_keys.sort()
        for plugin_name in plugin_keys:
            # Make sure the plugin has self.keys
            if hasattr(dict_of_plugins[plugin_name].PreparePlugin(), 'keys'):
                if not isinstance(dict_of_plugins[plugin_name].PreparePlugin().keys, list):
                    results['failed'] = True
                    results['msg'] = f"Plugin {plugin_name} must have a list of keys"
            else:
                results['failed'] = True
                results['msg'] = f"Plugin {plugin_name} must have a list of keys"
            # Call each plugin in a loop
            results = dict_of_plugins[plugin_name].PreparePlugin(
                host_name=ihn,
                hostvars=hvs,
                default_values=default_values,
                templates_path=tp,
                results=results).prepare()

            if results.get('failed'):
                # Check each plugin for failureds and break out of the loop early
                # if a failure is encounterd.
                break

        if results['failed']:
            # If there is a failure, remove the model data to make the failure message more readable
            results_copy = results.copy()
            for key in results_copy.keys():
                if key.startswith('model'):
                    del results[key]

        # Add golden untouched model data to results dictionary before returning
        results['model_golden'] = sm_data
        return results

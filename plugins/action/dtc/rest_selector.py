#!/usr/bin/python
# -*- coding: utf-8 -*-

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


display = Display()


class ActionModule(ActionBase):
    """
    Action plugin to dynamically select between cisco.nac_dc_vxlan.dtc.rest_selector and cisco.dcnm.dcnm_rest
    based on the ansible_network_os variable.
    """

    def run(self, tmp=None, task_vars=None):
        """
        Execute the action plugin.

        Args:
            tmp (str, optional): Temporary directory. Defaults to None.
            task_vars (dict, optional): Dictionary of task variables. Defaults to None.

        Returns:
            dict: Results of the REST API call
        """
        # Initialize results dictionary
        results = super(ActionModule, self).run(tmp, task_vars)
        results['changed'] = False
        results['failed'] = False

        # Get task arguments
        module_args = self._task.args.copy()
        
        # Get the network OS from task variables or module arguments
        network_os = task_vars.get('ansible_network_os') \
            or module_args.pop('ansible_network_os', None)
        
        # Determine which module to use based on network_os
        if network_os == 'cisco.nd.nd':
            rest_module = 'cisco.nac_dc_vxlan.dtc.rest_selector'
        elif network_os == 'cisco.dcnm.dcnm':
            rest_module = 'cisco.dcnm.dcnm_rest'
        else:
            results['failed'] = True
            results['msg'] = (
                f"Unsupported network_os: {network_os}. "
                "Must be 'cisco.nd.nd' or 'cisco.dcnm.dcnm'"
            )
            return results

        display.vvvv(f"Using REST module: {rest_module}")

        try:
            # Execute the appropriate REST module
            result = self._execute_module(
                module_name=rest_module,
                module_args=module_args,
                task_vars=task_vars,
                tmp=tmp
            )
            
            # Update results with the module's results
            if result.get('failed'):
                results.update(result)
            else:
                results['changed'] = result.get('changed', False)
                results.update(result)
                
        except Exception as e:
            results['failed'] = True
            results['msg'] = f"Failed to execute {rest_module}: {str(e)}"
            display.error(results['msg'], wrap_text=False)

        return results

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
DTC Pipeline Action Base — Shared ActionBase for pipeline-driven DTC plugins.

Provides the common Ansible ActionBase wrapper used by both manage_resources
and remove_resources. Handles parameter validation, verbose registry
validation, error handling, and changed aggregation.

Concrete subclasses implement _create_runner() to return the appropriate
pipeline runner (Factory Method pattern).
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from abc import abstractmethod

from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.registry_loader import (
    RegistryLoader,
)
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.ndfc_executor import (
    NdfcModuleExecutor,
)

display = Display()


class DtcPipelineActionBase(ActionBase):
    """
    Shared ActionBase for pipeline-driven DTC plugins.

    Handles parameter validation, verbose registry validation,
    error handling, and changed aggregation. Concrete subclasses
    implement _create_runner() to produce the appropriate pipeline runner.
    """

    REQUIRED_PARAMS = [
        'fabric_type', 'fabric_name', 'data_model', 'resource_data', 'change_flags',
    ]

    # Subclasses set this for error messages (e.g., 'Manage resources', 'Remove resources')
    OPERATION_LABEL = None

    @abstractmethod
    def _create_runner(self, params, executor, task_vars):
        """
        Factory method: return the concrete PipelineRunnerBase subclass.

        Args:
            params: Dict of task args from the role task YAML.
            executor: NdfcModuleExecutor instance.
            task_vars: Ansible task variables.

        Returns:
            A PipelineRunnerBase subclass instance.
        """

    def run(self, tmp=None, task_vars=None):
        results = super(DtcPipelineActionBase, self).run(tmp, task_vars)
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
            executor = NdfcModuleExecutor(self, task_vars, tmp)
            runner = self._create_runner(params, executor, task_vars)
            result = runner.run_pipeline()

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
            results['msg'] = f"{self.OPERATION_LABEL} failed: {str(e)}"

        return results

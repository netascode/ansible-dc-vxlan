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
Unit tests for manage_child_fabrics action plugin.
"""

from unittest.mock import patch

# Try to import from the plugins directory
try:
    from plugins.action.dtc.manage_child_fabrics import ActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.dtc.manage_child_fabrics import ActionModule
from .base_test import ActionModuleTestCase


class TestManageChildFabricsActionModule(ActionModuleTestCase):
    """Test cases for manage_child_fabrics action plugin."""

    def test_run_single_child_fabric_present(self):
        """Test run with single child fabric in present state."""
        parent_fabric = "parent-fabric"
        child_fabrics = ["single-child-fabric"]
        state = "present"

        # Mock successful response
        mock_response = {
            'changed': False,
            'failed': False
        }

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics,
            'state': state
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])
            self.assertTrue(result['child_fabrics_moved'])

    def test_run_present_state_success(self):
        """Test run with present state successful execution."""
        parent_fabric = "parent-fabric"
        child_fabrics = ["child-fabric1", "child-fabric2"]
        state = "present"

        mock_response = {
            'changed': False,
            'failed': False
        }

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics,
            'state': state
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])
            self.assertTrue(result['child_fabrics_moved'])

    def test_run_present_state_failure(self):
        """Test run with present state failed execution."""
        parent_fabric = "parent-fabric"
        child_fabrics = ["child-fabric1"]
        state = "present"

        mock_response = {
            'failed': True,
            'msg': {
                'MESSAGE': 'Bad Request',
                'DATA': 'Child fabric already exists'
            }
        }

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics,
            'state': state
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertTrue(result['failed'])
            self.assertIn('Bad Request', result['msg'])

    def test_run_absent_state_success(self):
        """Test run with absent state successful execution."""
        parent_fabric = "parent-fabric"
        child_fabrics = ["child-fabric1"]
        state = "absent"

        mock_response = {
            'changed': False,
            'failed': False
        }

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics,
            'state': state
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])

    def test_run_absent_state_failure(self):
        """Test run with absent state failed execution."""
        parent_fabric = "parent-fabric"
        child_fabrics = ["child-fabric1"]
        state = "absent"

        mock_response = {
            'failed': True,
            'msg': {
                'MESSAGE': 'Not Found',
                'DATA': 'Child fabric does not exist'
            }
        }

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics,
            'state': state
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertTrue(result['failed'])
            self.assertIn('Not Found', result['msg'])

    def test_run_mixed_success_failure_present(self):
        """Test run with mixed success and failure in present state."""
        parent_fabric = "parent-fabric"
        child_fabrics = ["child-fabric1", "child-fabric2"]
        state = "present"

        mock_responses = [
            {'changed': False, 'failed': False},  # First fabric succeeds
            {                                      # Second fabric fails
                'failed': True,
                'msg': {
                    'MESSAGE': 'Bad Request',
                    'DATA': 'Child fabric already exists'
                }
            }
        ]

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics,
            'state': state
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module to return different responses
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.side_effect = mock_responses

            result = action_module.run()

            # Should fail because second fabric failed
            self.assertTrue(result['failed'])
            self.assertIn('Bad Request', result['msg'])

    def test_run_json_data_format(self):
        """Test run verifies correct JSON data format for API calls."""
        parent_fabric = "parent-fabric"
        child_fabrics = ["child-fabric1"]
        state = "present"

        mock_response = {
            'changed': False,
            'failed': False
        }

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics,
            'state': state
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_response

            result = action_module.run()

            # Verify that _execute_module was called with correct arguments
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args[1]['module_args']

            self.assertEqual(call_args['method'], 'POST')
            self.assertEqual(call_args['path'], '/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/msdAdd')
            expected_json = '{"destFabric":"parent-fabric","sourceFabric":"child-fabric1"}'
            self.assertEqual(call_args['json_data'], expected_json)

    def test_run_empty_child_fabrics_list(self):
        """Test run with empty child fabrics list."""
        parent_fabric = "parent-fabric"
        child_fabrics = []
        state = "present"

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics,
            'state': state
        }

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertFalse(result['changed'])
        self.assertFalse(result['failed'])
        self.assertFalse(result['child_fabrics_moved'])

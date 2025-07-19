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
Unit tests for fabric_check_sync action plugin.
"""

import unittest
from unittest.mock import patch

# Try to import from the plugins directory
try:
    from plugins.action.dtc.fabric_check_sync import ActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.dtc.fabric_check_sync import ActionModule
from .base_test import ActionModuleTestCase


class TestFabricCheckSyncActionModule(ActionModuleTestCase):
    """Test cases for fabric_check_sync action plugin."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

    def test_run_all_switches_in_sync(self):
        """Test run when all switches are in sync."""
        fabric_name = "test_fabric"

        mock_response = {
            'response': {
                'DATA': [
                    {
                        'logicalName': 'switch1',
                        'ccStatus': 'In-Sync'
                    },
                    {
                        'logicalName': 'switch2',
                        'ccStatus': 'In-Sync'
                    },
                    {
                        'logicalName': 'switch3',
                        'ccStatus': 'In-Sync'
                    }
                ]
            }
        }

        task_args = {
            'fabric': fabric_name
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run:

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertFalse(result['failed'])

            # Verify the correct API call was made
            mock_execute.assert_called_once_with(
                module_name="cisco.dcnm.dcnm_rest",
                module_args={
                    "method": "GET",
                    "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/{fabric_name}/inventory/switchesByFabric",
                },
                task_vars=None,
                tmp=None
            )

    def test_run_switch_out_of_sync(self):
        """Test run when at least one switch is out of sync."""
        fabric_name = "test_fabric"

        mock_response = {
            'response': {
                'DATA': [
                    {
                        'logicalName': 'switch1',
                        'ccStatus': 'In-Sync'
                    },
                    {
                        'logicalName': 'switch2',
                        'ccStatus': 'Out-of-Sync'
                    },
                    {
                        'logicalName': 'switch3',
                        'ccStatus': 'In-Sync'
                    }
                ]
            }
        }

        task_args = {
            'fabric': fabric_name
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run:

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])

            # Verify the correct API call was made
            mock_execute.assert_called_once_with(
                module_name="cisco.dcnm.dcnm_rest",
                module_args={
                    "method": "GET",
                    "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/{fabric_name}/inventory/switchesByFabric",
                },
                task_vars=None,
                tmp=None
            )

    def test_run_multiple_switches_out_of_sync(self):
        """Test run when multiple switches are out of sync."""
        fabric_name = "test_fabric"

        mock_response = {
            'response': {
                'DATA': [
                    {
                        'logicalName': 'switch1',
                        'ccStatus': 'Out-of-Sync'
                    },
                    {
                        'logicalName': 'switch2',
                        'ccStatus': 'Out-of-Sync'
                    },
                    {
                        'logicalName': 'switch3',
                        'ccStatus': 'In-Sync'
                    }
                ]
            }
        }

        task_args = {
            'fabric': fabric_name
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run:

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.return_value = mock_response

            result = action_module.run()

            # Should detect out-of-sync and break early, so changed=True
            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])

    def test_run_empty_data(self):
        """Test run when DATA is empty."""
        fabric_name = "test_fabric"

        mock_response = {
            'response': {
                'DATA': []
            }
        }

        task_args = {
            'fabric': fabric_name
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run:

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertFalse(result['failed'])

    def test_run_no_data_key(self):
        """Test run when DATA key is missing."""
        fabric_name = "test_fabric"

        mock_response = {
            'response': {
                'OTHER_KEY': 'value'
            }
        }

        task_args = {
            'fabric': fabric_name
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run:

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertFalse(result['failed'])

    def test_run_null_data(self):
        """Test run when DATA is null."""
        fabric_name = "test_fabric"

        mock_response = {
            'response': {
                'DATA': None
            }
        }

        task_args = {
            'fabric': fabric_name
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run:

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertFalse(result['failed'])

    def test_run_missing_cc_status(self):
        """Test run when ccStatus is missing from switch data."""
        fabric_name = "test_fabric"

        mock_response = {
            'response': {
                'DATA': [
                    {
                        'logicalName': 'switch1'
                        # Missing ccStatus
                    }
                ]
            }
        }

        task_args = {
            'fabric': fabric_name
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run:

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.return_value = mock_response

            # Should raise KeyError when trying to access missing ccStatus
            with self.assertRaises(KeyError):
                action_module.run()

    def test_run_different_cc_status_values(self):
        """Test run with different ccStatus values."""
        fabric_name = "test_fabric"

        # Test various status values
        status_values = [
            ('In-Sync', False),  # (status, expected_changed)
            ('Out-of-Sync', True),
            ('Pending', False),
            ('Unknown', False),
            ('Error', False)
        ]

        for status, expected_changed in status_values:
            with self.subTest(status=status):
                mock_response = {
                    'response': {
                        'DATA': [
                            {
                                'logicalName': 'switch1',
                                'ccStatus': status
                            }
                        ]
                    }
                }

                task_args = {
                    'fabric': fabric_name
                }

                action_module = self.create_action_module(ActionModule, task_args)

                # Mock _execute_module method and ActionBase.run
                with patch.object(action_module, '_execute_module') as mock_execute, \
                     patch('ansible.plugins.action.ActionBase.run') as mock_parent_run:

                    mock_parent_run.return_value = {'changed': False, 'failed': False}
                    mock_execute.return_value = mock_response

                    result = action_module.run()

                    # Only 'Out-of-Sync' should cause changed=True
                    self.assertEqual(result['changed'], expected_changed)
                    self.assertFalse(result['failed'])

    def test_run_no_response_key(self):
        """Test run when response key is missing."""
        fabric_name = "test_fabric"

        mock_response = {}

        task_args = {
            'fabric': fabric_name
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run:

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.return_value = mock_response

            # Should raise KeyError when trying to access response
            with self.assertRaises(KeyError):
                action_module.run()


if __name__ == '__main__':
    unittest.main()

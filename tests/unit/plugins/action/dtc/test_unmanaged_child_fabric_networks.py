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
Unit tests for unmanaged_child_fabric_networks action plugin.
"""

import unittest
from unittest.mock import patch

# Try to import from the plugins directory
try:
    from plugins.action.dtc.unmanaged_child_fabric_networks import ActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.dtc.unmanaged_child_fabric_networks import ActionModule
from .base_test import ActionModuleTestCase


class TestUnmanagedChildFabricNetworksActionModule(ActionModuleTestCase):
    """Test cases for unmanaged_child_fabric_networks action plugin."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.maxDiff = None

        self.mock_task_args = {
            'fabric': 'test_fabric',
            'msite_data': {
                'overlay_attach_groups': {
                    'networks': [
                        {'name': 'managed_network_1'},
                        {'name': 'managed_network_2'}
                    ]
                }
            }
        }

    def test_run_no_networks_in_ndfc(self):
        """Test run when NDFC has no networks."""
        action_module = self.create_action_module(ActionModule, self.mock_task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC query returning no networks
            mock_execute.return_value = {
                'response': []
            }

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertFalse(result['failed'])
            self.assertEqual(mock_execute.call_count, 1)

    def test_run_ndfc_query_failed(self):
        """Test run when NDFC query fails."""
        action_module = self.create_action_module(ActionModule, self.mock_task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC query failure
            mock_execute.return_value = {
                'failed': True,
                'msg': 'Fabric test_fabric missing on DCNM or does not have any switches'
            }

            result = action_module.run()

            self.assertTrue(result['failed'])
            self.assertIn('Fabric test_fabric missing', result['msg'])
            self.assertEqual(mock_execute.call_count, 1)

    def test_run_no_unmanaged_networks(self):
        """Test run when all NDFC networks are managed."""
        action_module = self.create_action_module(ActionModule, self.mock_task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC query returning only managed networks
            mock_execute.return_value = {
                'response': [
                    {
                        'parent': {
                            'networkName': 'managed_network_1'
                        }
                    },
                    {
                        'parent': {
                            'networkName': 'managed_network_2'
                        }
                    }
                ]
            }

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertFalse(result['failed'])
            self.assertEqual(mock_execute.call_count, 1)

    def test_run_with_unmanaged_networks_delete_success(self):
        """Test run when unmanaged networks are found and successfully deleted."""
        action_module = self.create_action_module(ActionModule, self.mock_task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC query returning managed + unmanaged networks
            mock_execute.side_effect = [
                # First call: query networks
                {
                    'response': [
                        {
                            'parent': {
                                'networkName': 'managed_network_1'
                            }
                        },
                        {
                            'parent': {
                                'networkName': 'unmanaged_network_1'
                            }
                        },
                        {
                            'parent': {
                                'networkName': 'unmanaged_network_2'
                            }
                        }
                    ]
                },
                # Second call: delete unmanaged networks (success)
                {
                    'changed': True
                }
            ]

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])
            self.assertEqual(mock_execute.call_count, 2)

            # Verify the delete call was made with correct config
            delete_call_args = mock_execute.call_args_list[1]
            delete_config = delete_call_args[1]['module_args']['config']
            self.assertEqual(len(delete_config), 2)
            self.assertEqual(delete_config[0]['net_name'], 'unmanaged_network_1')
            self.assertEqual(delete_config[1]['net_name'], 'unmanaged_network_2')
            self.assertTrue(delete_config[0]['deploy'])
            self.assertTrue(delete_config[1]['deploy'])

    def test_run_with_unmanaged_networks_delete_failed(self):
        """Test run when unmanaged networks deletion fails."""
        action_module = self.create_action_module(ActionModule, self.mock_task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC query returning unmanaged networks
            mock_execute.side_effect = [
                # First call: query networks
                {
                    'response': [
                        {
                            'parent': {
                                'networkName': 'managed_network_1'
                            }
                        },
                        {
                            'parent': {
                                'networkName': 'unmanaged_network_1'
                            }
                        }
                    ]
                },
                # Second call: delete unmanaged networks (fails)
                {
                    'failed': True,
                    'msg': 'Failed to delete network unmanaged_network_1'
                }
            ]

            result = action_module.run()

            self.assertTrue(result['failed'])
            self.assertIn('Failed to delete network', result['msg'])
            self.assertEqual(mock_execute.call_count, 2)

    def test_run_ndfc_networks_no_response_key(self):
        """Test run when NDFC query succeeds but has no response key."""
        action_module = self.create_action_module(ActionModule, self.mock_task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC query without response key
            mock_execute.return_value = {
                'changed': False
            }

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertFalse(result['failed'])
            self.assertEqual(mock_execute.call_count, 1)

    def test_run_empty_managed_networks_list(self):
        """Test run when data model has no managed networks."""
        task_args = {
            'fabric': 'test_fabric',
            'msite_data': {
                'overlay_attach_groups': {
                    'networks': []
                }
            }
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC query returning some networks
            mock_execute.side_effect = [
                # First call: query networks
                {
                    'response': [
                        {
                            'parent': {
                                'networkName': 'unmanaged_network_1'
                            }
                        },
                        {
                            'parent': {
                                'networkName': 'unmanaged_network_2'
                            }
                        }
                    ]
                },
                # Second call: delete all networks (success)
                {
                    'changed': True
                }
            ]

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])
            self.assertEqual(mock_execute.call_count, 2)

    def test_run_mixed_network_scenarios(self):
        """Test run with various network name patterns."""
        task_args = {
            'fabric': 'test_fabric',
            'msite_data': {
                'overlay_attach_groups': {
                    'networks': [
                        {'name': 'prod_network'},
                        {'name': 'test_network_123'},
                        {'name': 'special-chars_network'}
                    ]
                }
            }
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC query with mixed managed/unmanaged networks
            mock_execute.side_effect = [
                # First call: query networks
                {
                    'response': [
                        {
                            'parent': {
                                'networkName': 'prod_network'  # managed
                            }
                        },
                        {
                            'parent': {
                                'networkName': 'old_unmanaged_net'  # unmanaged
                            }
                        },
                        {
                            'parent': {
                                'networkName': 'test_network_123'  # managed
                            }
                        },
                        {
                            'parent': {
                                'networkName': 'legacy_network'  # unmanaged
                            }
                        }
                    ]
                },
                # Second call: delete unmanaged networks (success)
                {
                    'changed': True
                }
            ]

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])
            self.assertEqual(mock_execute.call_count, 2)

            # Verify only unmanaged networks were marked for deletion
            delete_call_args = mock_execute.call_args_list[1]
            delete_config = delete_call_args[1]['module_args']['config']
            unmanaged_names = [config['net_name'] for config in delete_config]
            self.assertIn('old_unmanaged_net', unmanaged_names)
            self.assertIn('legacy_network', unmanaged_names)
            self.assertNotIn('prod_network', unmanaged_names)
            self.assertNotIn('test_network_123', unmanaged_names)


if __name__ == '__main__':
    unittest.main()

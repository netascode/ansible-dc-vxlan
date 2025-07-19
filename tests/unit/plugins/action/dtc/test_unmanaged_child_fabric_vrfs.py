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
Unit tests for unmanaged_child_fabric_vrfs action plugin.
"""

import unittest
from unittest.mock import patch

# Try to import from the plugins directory
try:
    from plugins.action.dtc.unmanaged_child_fabric_vrfs import ActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.dtc.unmanaged_child_fabric_vrfs import ActionModule
from .base_test import ActionModuleTestCase


class TestUnmanagedChildFabricVrfsActionModule(ActionModuleTestCase):
    """Test cases for unmanaged_child_fabric_vrfs action plugin."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.maxDiff = None

        self.mock_task_args = {
            'fabric': 'test_fabric',
            'msite_data': {
                'overlay_attach_groups': {
                    'vrfs': [
                        {'name': 'managed_vrf_1'},
                        {'name': 'managed_vrf_2'}
                    ]
                }
            }
        }

    def test_run_no_vrfs_in_ndfc(self):
        """Test run when NDFC has no VRFs."""
        action_module = self.create_action_module(ActionModule, self.mock_task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC query returning no VRFs
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

    def test_run_no_unmanaged_vrfs(self):
        """Test run when all NDFC VRFs are managed."""
        action_module = self.create_action_module(ActionModule, self.mock_task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC query returning only managed VRFs
            mock_execute.return_value = {
                'response': [
                    {
                        'parent': {
                            'vrfName': 'managed_vrf_1'
                        }
                    },
                    {
                        'parent': {
                            'vrfName': 'managed_vrf_2'
                        }
                    }
                ]
            }

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertFalse(result['failed'])
            self.assertEqual(mock_execute.call_count, 1)

    def test_run_with_unmanaged_vrfs_delete_success(self):
        """Test run when unmanaged VRFs are found and successfully deleted."""
        action_module = self.create_action_module(ActionModule, self.mock_task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC query returning managed + unmanaged VRFs
            mock_execute.side_effect = [
                # First call: query VRFs
                {
                    'response': [
                        {
                            'parent': {
                                'vrfName': 'managed_vrf_1'
                            }
                        },
                        {
                            'parent': {
                                'vrfName': 'unmanaged_vrf_1'
                            }
                        },
                        {
                            'parent': {
                                'vrfName': 'unmanaged_vrf_2'
                            }
                        }
                    ]
                },
                # Second call: delete unmanaged VRFs (success)
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
            self.assertEqual(delete_config[0]['vrf_name'], 'unmanaged_vrf_1')
            self.assertEqual(delete_config[1]['vrf_name'], 'unmanaged_vrf_2')
            self.assertTrue(delete_config[0]['deploy'])
            self.assertTrue(delete_config[1]['deploy'])

    def test_run_with_unmanaged_vrfs_delete_failed(self):
        """Test run when unmanaged VRFs deletion fails."""
        action_module = self.create_action_module(ActionModule, self.mock_task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC query returning unmanaged VRFs
            mock_execute.side_effect = [
                # First call: query VRFs
                {
                    'response': [
                        {
                            'parent': {
                                'vrfName': 'managed_vrf_1'
                            }
                        },
                        {
                            'parent': {
                                'vrfName': 'unmanaged_vrf_1'
                            }
                        }
                    ]
                },
                # Second call: delete unmanaged VRFs (fails)
                {
                    'failed': True,
                    'msg': 'Failed to delete VRF unmanaged_vrf_1'
                }
            ]

            result = action_module.run()

            self.assertTrue(result['failed'])
            self.assertIn('Failed to delete VRF', result['msg'])
            self.assertEqual(mock_execute.call_count, 2)

    def test_run_ndfc_vrfs_no_response_key(self):
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

    def test_run_empty_managed_vrfs_list(self):
        """Test run when data model has no managed VRFs."""
        task_args = {
            'fabric': 'test_fabric',
            'msite_data': {
                'overlay_attach_groups': {
                    'vrfs': []
                }
            }
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC query returning some VRFs
            mock_execute.side_effect = [
                # First call: query VRFs
                {
                    'response': [
                        {
                            'parent': {
                                'vrfName': 'unmanaged_vrf_1'
                            }
                        },
                        {
                            'parent': {
                                'vrfName': 'unmanaged_vrf_2'
                            }
                        }
                    ]
                },
                # Second call: delete all VRFs (success)
                {
                    'changed': True
                }
            ]

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])
            self.assertEqual(mock_execute.call_count, 2)

    def test_run_mixed_vrf_scenarios(self):
        """Test run with various VRF name patterns."""
        task_args = {
            'fabric': 'test_fabric',
            'msite_data': {
                'overlay_attach_groups': {
                    'vrfs': [
                        {'name': 'prod_vrf'},
                        {'name': 'test_vrf_123'},
                        {'name': 'special-chars_vrf'}
                    ]
                }
            }
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC query with mixed managed/unmanaged VRFs
            mock_execute.side_effect = [
                # First call: query VRFs
                {
                    'response': [
                        {
                            'parent': {
                                'vrfName': 'prod_vrf'  # managed
                            }
                        },
                        {
                            'parent': {
                                'vrfName': 'old_unmanaged_vrf'  # unmanaged
                            }
                        },
                        {
                            'parent': {
                                'vrfName': 'test_vrf_123'  # managed
                            }
                        },
                        {
                            'parent': {
                                'vrfName': 'legacy_vrf'  # unmanaged
                            }
                        }
                    ]
                },
                # Second call: delete unmanaged VRFs (success)
                {
                    'changed': True
                }
            ]

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])
            self.assertEqual(mock_execute.call_count, 2)

            # Verify only unmanaged VRFs were marked for deletion
            delete_call_args = mock_execute.call_args_list[1]
            delete_config = delete_call_args[1]['module_args']['config']
            unmanaged_names = [config['vrf_name'] for config in delete_config]
            self.assertIn('old_unmanaged_vrf', unmanaged_names)
            self.assertIn('legacy_vrf', unmanaged_names)
            self.assertNotIn('prod_vrf', unmanaged_names)
            self.assertNotIn('test_vrf_123', unmanaged_names)

    def test_run_vrf_query_with_complex_response(self):
        """Test run with complex NDFC VRF response structure."""
        action_module = self.create_action_module(ActionModule, self.mock_task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC query with complex response structure
            mock_execute.side_effect = [
                # First call: query VRFs with full response structure
                {
                    'response': [
                        {
                            'parent': {
                                'fabric': 'test_fabric',
                                'vrfName': 'managed_vrf_1',
                                'enforce': 'None',
                                'defaultSGTag': 'None',
                                'vrfTemplate': 'Default_VRF_Universal',
                                'vrfExtensionTemplate': 'Default_VRF_Extension_Universal',
                                'vrfTemplateConfig': '{"vrfName":"managed_vrf_1"}',
                                'tenantName': 'None',
                                'id': 123,
                                'vrfId': 150001,
                                'serviceVrfTemplate': 'None',
                                'source': 'None',
                                'vrfStatus': 'DEPLOYED',
                                'hierarchicalKey': 'test_fabric'
                            },
                            'attach': [
                                {
                                    'vrfName': 'managed_vrf_1',
                                    'templateName': 'Default_VRF_Universal',
                                    'switchDetailsList': []
                                }
                            ]
                        },
                        {
                            'parent': {
                                'fabric': 'test_fabric',
                                'vrfName': 'legacy_unmanaged_vrf',
                                'vrfStatus': 'DEPLOYED'
                            },
                            'attach': []
                        }
                    ]
                },
                # Second call: delete unmanaged VRFs (success)
                {
                    'changed': True
                }
            ]

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])
            self.assertEqual(mock_execute.call_count, 2)

            # Verify the correct VRF was marked for deletion
            delete_call_args = mock_execute.call_args_list[1]
            delete_config = delete_call_args[1]['module_args']['config']
            self.assertEqual(len(delete_config), 1)
            self.assertEqual(delete_config[0]['vrf_name'], 'legacy_unmanaged_vrf')
            self.assertTrue(delete_config[0]['deploy'])


if __name__ == '__main__':
    unittest.main()

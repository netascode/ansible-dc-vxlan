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
Unit tests for unmanaged_policy action plugin.
"""

from unittest.mock import patch

# Try to import from the plugins directory
try:
    from plugins.action.dtc.unmanaged_policy import ActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.dtc.unmanaged_policy import ActionModule
from .base_test import ActionModuleTestCase


class TestUnmanagedPolicyActionModule(ActionModuleTestCase):
    """Test cases for unmanaged_policy action plugin."""

    def test_run_no_unmanaged_policies(self):
        """Test run when there are no unmanaged policies."""
        switch_serial_numbers = ["ABC123"]
        model_data = {
            "vxlan": {
                "topology": {
                    "switches": [
                        {
                            "serial_number": "ABC123",
                            "management": {
                                "management_ipv4_address": "10.1.1.1"
                            }
                        }
                    ]
                },
                "policy": {
                    "policies": [],
                    "groups": [
                        {
                            "name": "group1",
                            "policies": [
                                {"name": "Test Policy"}
                            ]
                        }
                    ],
                    "switches": [
                        {
                            "mgmt_ip_address": "10.1.1.1",
                            "groups": ["group1"]
                        }
                    ]
                }
            }
        }

        # NDFC returns policies that match the data model
        mock_ndfc_policies = [
            {
                "policyId": "policy_123",
                "description": "nac_Test_Policy"
            }
        ]

        task_args = {
            'switch_serial_numbers': switch_serial_numbers,
            'model_data': model_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Only mock the helper function, not the parent run()
        with patch('plugins.action.dtc.unmanaged_policy.ndfc_get_switch_policy_using_desc') as mock_helper:
            mock_helper.return_value = mock_ndfc_policies

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertIn('unmanaged_policies', result)
            self.assertEqual(result['unmanaged_policies'], [{'switch': []}])

    def test_run_with_unmanaged_policies(self):
        """Test run when there are unmanaged policies."""
        switch_serial_numbers = ["ABC123"]
        model_data = {
            "vxlan": {
                "topology": {
                    "switches": [
                        {
                            "serial_number": "ABC123",
                            "management": {
                                "management_ipv4_address": "10.1.1.1"
                            }
                        }
                    ]
                },
                "policy": {
                    "policies": [],
                    "groups": [
                        {
                            "name": "group1",
                            "policies": [
                                {"name": "Managed Policy"}
                            ]
                        }
                    ],
                    "switches": [
                        {
                            "mgmt_ip_address": "10.1.1.1",
                            "groups": ["group1"]
                        }
                    ]
                }
            }
        }

        # NDFC returns policies including unmanaged ones
        mock_ndfc_policies = [
            {
                "policyId": "policy_123",
                "description": "nac_Managed_Policy"  # This is managed
            },
            {
                "policyId": "policy_456",
                "description": "nac_Unmanaged_Policy"  # This is unmanaged
            }
        ]

        task_args = {
            'switch_serial_numbers': switch_serial_numbers,
            'model_data': model_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Only mock the helper function, not the parent run()
        with patch('plugins.action.dtc.unmanaged_policy.ndfc_get_switch_policy_using_desc') as mock_helper:
            mock_helper.return_value = mock_ndfc_policies

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertIn('unmanaged_policies', result)
            # Should have one switch with unmanaged policies
            self.assertEqual(len(result['unmanaged_policies'][0]['switch']), 1)
            self.assertEqual(result['unmanaged_policies'][0]['switch'][0]['ip'], '10.1.1.1')
            # Should have one unmanaged policy
            self.assertEqual(len(result['unmanaged_policies'][0]['switch'][0]['policies']), 1)
            self.assertEqual(result['unmanaged_policies'][0]['switch'][0]['policies'][0]['name'], 'policy_456')
            self.assertEqual(result['unmanaged_policies'][0]['switch'][0]['policies'][0]['description'], 'nac_Unmanaged_Policy')

    def test_run_multiple_switches_mixed_policies(self):
        """Test run with multiple switches having mixed policies."""
        switch_serial_numbers = ["ABC123", "DEF456"]
        model_data = {
            "vxlan": {
                "topology": {
                    "switches": [
                        {
                            "serial_number": "ABC123",
                            "management": {
                                "management_ipv4_address": "10.1.1.1"
                            }
                        },
                        {
                            "serial_number": "DEF456",
                            "management": {
                                "management_ipv4_address": "10.1.1.2"
                            }
                        }
                    ]
                },
                "policy": {
                    "policies": [],
                    "groups": [
                        {
                            "name": "group1",
                            "policies": [
                                {"name": "Policy 1"}
                            ]
                        }
                    ],
                    "switches": [
                        {
                            "mgmt_ip_address": "10.1.1.1",
                            "groups": ["group1"]
                        },
                        {
                            "mgmt_ip_address": "10.1.1.2",
                            "groups": ["group1"]
                        }
                    ]
                }
            }
        }

        def mock_helper_side_effect(self, task_vars, tmp, serial, prefix):
            if serial == "ABC123":
                # First switch has an unmanaged policy
                return [
                    {"policyId": "policy_123", "description": "nac_Policy_1"},
                    {"policyId": "policy_999", "description": "nac_Unmanaged_Policy"}
                ]
            else:  # DEF456
                # Second switch has only managed policies
                return [
                    {"policyId": "policy_456", "description": "nac_Policy_1"}
                ]

        task_args = {
            'switch_serial_numbers': switch_serial_numbers,
            'model_data': model_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch('plugins.action.dtc.unmanaged_policy.ndfc_get_switch_policy_using_desc') as mock_helper:
            mock_helper.side_effect = mock_helper_side_effect

            result = action_module.run()

            self.assertTrue(result['changed'])
            # Should have only one switch with unmanaged policies
            self.assertEqual(len(result['unmanaged_policies'][0]['switch']), 1)
            self.assertEqual(result['unmanaged_policies'][0]['switch'][0]['ip'], '10.1.1.1')

    def test_run_ipv6_management_address(self):
        """Test run with IPv6 management address."""
        switch_serial_numbers = ["ABC123"]
        model_data = {
            "vxlan": {
                "topology": {
                    "switches": [
                        {
                            "serial_number": "ABC123",
                            "management": {
                                "management_ipv6_address": "2001:db8::1"
                            }
                        }
                    ]
                },
                "policy": {
                    "policies": [],
                    "groups": [
                        {
                            "name": "group1",
                            "policies": [
                                {"name": "Policy 1"}
                            ]
                        }
                    ],
                    "switches": [
                        {
                            "mgmt_ip_address": "2001:db8::1",
                            "groups": ["group1"]
                        }
                    ]
                }
            }
        }

        mock_ndfc_policies = [
            {
                "policyId": "policy_999",
                "description": "nac_Unmanaged_Policy"
            }
        ]

        task_args = {
            'switch_serial_numbers': switch_serial_numbers,
            'model_data': model_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch('plugins.action.dtc.unmanaged_policy.ndfc_get_switch_policy_using_desc') as mock_helper:
            mock_helper.return_value = mock_ndfc_policies

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertEqual(result['unmanaged_policies'][0]['switch'][0]['ip'], '2001:db8::1')

    def test_run_switch_not_in_model(self):
        """Test run when switch is not found in data model."""
        switch_serial_numbers = ["XYZ999"]  # Not in model
        model_data = {
            "vxlan": {
                "topology": {
                    "switches": [
                        {
                            "serial_number": "ABC123",
                            "management": {
                                "management_ipv4_address": "10.1.1.1"
                            }
                        }
                    ]
                },
                "policy": {
                    "policies": [],
                    "groups": [],
                    "switches": []
                }
            }
        }

        mock_ndfc_policies = []

        task_args = {
            'switch_serial_numbers': switch_serial_numbers,
            'model_data': model_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch('plugins.action.dtc.unmanaged_policy.ndfc_get_switch_policy_using_desc') as mock_helper:
            mock_helper.return_value = mock_ndfc_policies

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertEqual(result['unmanaged_policies'], [{'switch': []}])

    def test_run_missing_management_addresses(self):
        """Test run when management addresses are missing."""
        switch_serial_numbers = ["ABC123"]
        model_data = {
            "vxlan": {
                "topology": {
                    "switches": [
                        {
                            "serial_number": "ABC123",
                            "management": {}  # No IP addresses
                        }
                    ]
                },
                "policy": {
                    "policies": [],
                    "groups": [],
                    "switches": []
                }
            }
        }

        mock_ndfc_policies = []

        task_args = {
            'switch_serial_numbers': switch_serial_numbers,
            'model_data': model_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch('plugins.action.dtc.unmanaged_policy.ndfc_get_switch_policy_using_desc') as mock_helper:
            mock_helper.return_value = mock_ndfc_policies

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertIn('unmanaged_policies', result)

    def test_run_empty_switch_serial_numbers(self):
        """Test run with empty switch serial numbers list."""
        switch_serial_numbers = []
        model_data = {
            "vxlan": {
                "topology": {
                    "switches": []
                },
                "policy": {
                    "policies": [],
                    "groups": [],
                    "switches": []
                }
            }
        }

        task_args = {
            'switch_serial_numbers': switch_serial_numbers,
            'model_data': model_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertFalse(result['changed'])
        self.assertIn('unmanaged_policies', result)
        self.assertEqual(result['unmanaged_policies'], [{'switch': []}])

    def test_run_policy_name_formatting(self):
        """Test run verifies correct policy name formatting (spaces to underscores)."""
        switch_serial_numbers = ["ABC123"]
        model_data = {
            "vxlan": {
                "topology": {
                    "switches": [
                        {
                            "serial_number": "ABC123",
                            "management": {
                                "management_ipv4_address": "10.1.1.1"
                            }
                        }
                    ]
                },
                "policy": {
                    "policies": [],
                    "groups": [
                        {
                            "name": "group1",
                            "policies": [
                                {"name": "Policy With Spaces"}  # Spaces should become underscores
                            ]
                        }
                    ],
                    "switches": [
                        {
                            "mgmt_ip_address": "10.1.1.1",
                            "groups": ["group1"]
                        }
                    ]
                }
            }
        }

        # NDFC returns policy that doesn't match due to formatting
        mock_ndfc_policies = [
            {
                "policyId": "policy_123",
                "description": "nac_Policy_With_Spaces"  # Matches formatted name
            },
            {
                "policyId": "policy_456",
                "description": "nac_Unmanaged Policy"  # Different formatting - unmanaged
            }
        ]

        task_args = {
            'switch_serial_numbers': switch_serial_numbers,
            'model_data': model_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch('plugins.action.dtc.unmanaged_policy.ndfc_get_switch_policy_using_desc') as mock_helper:
            mock_helper.return_value = mock_ndfc_policies

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertIn('unmanaged_policies', result)
            # Should detect the unmanaged policy due to formatting difference
            self.assertEqual(len(result['unmanaged_policies'][0]['switch']), 1)

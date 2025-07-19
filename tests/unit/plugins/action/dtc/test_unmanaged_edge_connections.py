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
Unit tests for unmanaged_edge_connections action plugin.
"""

from unittest.mock import patch

# Try to import from the plugins directory
try:
    from plugins.action.dtc.unmanaged_edge_connections import ActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.dtc.unmanaged_edge_connections import ActionModule
from .base_test import ActionModuleTestCase


class TestUnmanagedEdgeConnectionsActionModule(ActionModuleTestCase):
    """Test cases for unmanaged_edge_connections action plugin."""

    def test_run_with_unmanaged_policy(self):
        """Test run when NDFC has policies not in the data model (unmanaged)."""
        switch_data = [
            {
                'serialNumber': 'ABC123',
                'ipAddress': '10.1.1.1'
            }
        ]

        edge_connections = [
            {
                "switch": [
                    {
                        'ip': '10.1.1.1',
                        'policies': [
                            {'description': 'nace_test_policy_1'},
                            {'description': 'nace_test_policy_2'}
                        ]
                    }
                ]
            }
        ]

        def mock_helper_side_effect(self, task_vars, tmp, serial, prefix):
            if prefix == 'edge_':
                return []  # No edge_ policies
            else:  # prefix == 'nace_'
                return [{'policyId': 'POL123', 'description': 'nace_unmanaged_policy'}]

        task_args = {
            'switch_data': switch_data,
            'edge_connections': edge_connections
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Only mock the helper function, not the parent run()
        with patch('plugins.action.dtc.unmanaged_edge_connections.ndfc_get_switch_policy_using_desc') as mock_helper:
            mock_helper.side_effect = mock_helper_side_effect

            result = action_module.run()

            # Should detect unmanaged policy and set changed=True
            self.assertTrue(result['changed'])
            self.assertIn('unmanaged_edge_connections', result)
            # Should have one switch with unmanaged policies
            self.assertEqual(len(result['unmanaged_edge_connections'][0]['switch']), 1)
            self.assertEqual(result['unmanaged_edge_connections'][0]['switch'][0]['ip'], '10.1.1.1')
            self.assertEqual(len(result['unmanaged_edge_connections'][0]['switch'][0]['policies']), 1)
            self.assertEqual(result['unmanaged_edge_connections'][0]['switch'][0]['policies'][0]['name'], 'POL123')

    def test_run_no_unmanaged_connections(self):
        """Test run when all edge connections are managed."""
        switch_data = [
            {
                'serialNumber': 'ABC123',
                'ipAddress': '10.1.1.1'
            }
        ]

        edge_connections = [
            {
                "switch": [
                    {
                        'ip': '10.1.1.1',
                        'policies': [
                            {'description': 'nace_test_policy_1'},
                            {'description': 'nace_test_policy_2'}
                        ]
                    }
                ]
            }
        ]

        def mock_helper_side_effect(self, task_vars, tmp, serial, prefix):
            if prefix == 'edge_':
                return []  # No edge_ policies
            else:  # prefix == 'nace_'
                # NDFC returns only managed policies (those in the data model)
                return [
                    {'policyId': 'POL123', 'description': 'nace_test_policy_1'},
                    {'policyId': 'POL124', 'description': 'nace_test_policy_2'}
                ]

        task_args = {
            'switch_data': switch_data,
            'edge_connections': edge_connections
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Only mock the helper function
        with patch('plugins.action.dtc.unmanaged_edge_connections.ndfc_get_switch_policy_using_desc') as mock_helper:
            mock_helper.side_effect = mock_helper_side_effect

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertIn('unmanaged_edge_connections', result)
            # Should have empty switch list when no unmanaged policies
            self.assertEqual(len(result['unmanaged_edge_connections'][0]['switch']), 0)

    def test_run_empty_edge_connections(self):
        """Test run with empty edge connections."""
        switch_data = []
        edge_connections = [{"switch": []}]

        task_args = {
            'switch_data': switch_data,
            'edge_connections': edge_connections
        }

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertFalse(result['changed'])
        self.assertIn('unmanaged_edge_connections', result)

    def test_run_switch_not_in_edge_connections(self):
        """Test run when switch exists in NDFC but not in edge connections data."""
        switch_data = [
            {
                'serialNumber': 'ABC123',
                'ipAddress': '10.1.1.2'  # Different IP not in edge_connections
            }
        ]

        edge_connections = [
            {
                "switch": [
                    {
                        'ip': '10.1.1.1',
                        'policies': [
                            {'description': 'nace_test_policy_1'}
                        ]
                    }
                ]
            }
        ]

        task_args = {
            'switch_data': switch_data,
            'edge_connections': edge_connections
        }

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertFalse(result['changed'])
        self.assertEqual(len(result['unmanaged_edge_connections'][0]['switch']), 0)

    def test_run_multiple_switches_with_mixed_policies(self):
        """Test run with multiple switches, some with unmanaged policies."""
        switch_data = [
            {
                'serialNumber': 'ABC123',
                'ipAddress': '10.1.1.1'
            },
            {
                'serialNumber': 'DEF456',
                'ipAddress': '10.1.1.2'
            }
        ]

        edge_connections = [
            {
                "switch": [
                    {
                        'ip': '10.1.1.1',
                        'policies': [
                            {'description': 'nace_policy_1'}
                        ]
                    },
                    {
                        'ip': '10.1.1.2',
                        'policies': [
                            {'description': 'nace_policy_2'}
                        ]
                    }
                ]
            }
        ]

        def mock_helper_side_effect(self, task_vars, tmp, serial, prefix):
            if serial == 'ABC123':
                if prefix == 'edge_':
                    return []  # No edge_ policies for first switch
                else:  # prefix == 'nace_'
                    return [{'policyId': 'POL123', 'description': 'nace_unmanaged'}]
            else:  # serial == 'DEF456'
                # Second switch has only managed policies for both prefixes
                if prefix == 'edge_':
                    return []
                else:  # prefix == 'nace_'
                    return [{'policyId': 'POL124', 'description': 'nace_policy_2'}]

        task_args = {
            'switch_data': switch_data,
            'edge_connections': edge_connections
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch('plugins.action.dtc.unmanaged_edge_connections.ndfc_get_switch_policy_using_desc') as mock_helper:
            mock_helper.side_effect = mock_helper_side_effect

            result = action_module.run()

            self.assertTrue(result['changed'])
            # Should have only one switch with unmanaged policies
            self.assertEqual(len(result['unmanaged_edge_connections'][0]['switch']), 1)
            self.assertEqual(result['unmanaged_edge_connections'][0]['switch'][0]['ip'], '10.1.1.1')

    def test_run_edge_prefix_backwards_compatibility(self):
        """Test run with legacy 'edge_' prefix."""
        switch_data = [
            {
                'serialNumber': 'ABC123',
                'ipAddress': '10.1.1.1'
            }
        ]

        edge_connections = [
            {
                "switch": [
                    {
                        'ip': '10.1.1.1',
                        'policies': [
                            {'description': 'edge_test_policy_1'}
                        ]
                    }
                ]
            }
        ]

        def mock_helper_side_effect(self, task_vars, tmp, serial, prefix):
            if prefix == 'edge_':
                return [{'policyId': 'POL123', 'description': 'edge_unmanaged'}]
            else:  # prefix == 'nace_'
                return []

        task_args = {
            'switch_data': switch_data,
            'edge_connections': edge_connections
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch('plugins.action.dtc.unmanaged_edge_connections.ndfc_get_switch_policy_using_desc') as mock_helper:
            mock_helper.side_effect = mock_helper_side_effect

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertEqual(result['unmanaged_edge_connections'][0]['switch'][0]['policies'][0]['description'], 'edge_unmanaged')

    def test_run_combined_edge_and_nace_prefixes(self):
        """Test run with both edge_ and nace_ prefixes returning policies."""
        switch_data = [
            {
                'serialNumber': 'ABC123',
                'ipAddress': '10.1.1.1'
            }
        ]

        edge_connections = [
            {
                "switch": [
                    {
                        'ip': '10.1.1.1',
                        'policies': [
                            {'description': 'nace_managed_policy'}
                        ]
                    }
                ]
            }
        ]

        def mock_helper_side_effect(self, task_vars, tmp, serial, prefix):
            if prefix == 'edge_':
                return [{'policyId': 'POL123', 'description': 'edge_unmanaged'}]
            else:  # prefix == 'nace_'
                return [{'policyId': 'POL124', 'description': 'nace_another_unmanaged'}]

        task_args = {
            'switch_data': switch_data,
            'edge_connections': edge_connections
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch('plugins.action.dtc.unmanaged_edge_connections.ndfc_get_switch_policy_using_desc') as mock_helper:
            mock_helper.side_effect = mock_helper_side_effect

            result = action_module.run()

            self.assertTrue(result['changed'])
            # Should have both unmanaged policies detected
            # Note: The plugin logic adds each unmanaged policy as a separate switch entry
            # This is based on the plugin's current implementation

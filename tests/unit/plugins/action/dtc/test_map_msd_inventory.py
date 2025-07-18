"""
Unit tests for map_msd_inventory action plugin.
"""
import pytest
from unittest.mock import patch

from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.map_msd_inventory import ActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.base_test import ActionModuleTestCase


class TestMapMsdInventoryActionModule(ActionModuleTestCase):
    """Test cases for map_msd_inventory action plugin."""

    def test_run_successful_inventory_query(self):
        """Test run with successful inventory query."""
        parent_fabric_name = "msd-fabric"
        model_data_overlay = {
            'vrf_attach_switches_list': ['switch1', '10.1.1.1'],
            'network_attach_switches_list': ['switch2', '10.1.1.2']
        }

        mock_inventory_response = {
            'response': [
                {
                    'hostName': 'switch1',
                    'ipAddress': '10.1.1.1',
                    'fabricName': 'child-fabric1'
                },
                {
                    'hostName': 'switch2',
                    'ipAddress': '10.1.1.2',
                    'fabricName': 'child-fabric2'
                }
            ]
        }

        task_args = {
            'parent_fabric_name': parent_fabric_name,
            'model_data_overlay': model_data_overlay
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_inventory_response

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertIn('msd_switches', result)
            self.assertIn('switch1', result['msd_switches'])
            self.assertIn('10.1.1.1', result['msd_switches'])

    def test_run_switch_mapping_behavior(self):
        """Test run verifies switch mapping behavior."""
        parent_fabric_name = "msd-fabric"
        model_data_overlay = {
            'vrf_attach_switches_list': [],
            'network_attach_switches_list': []
        }

        mock_inventory_response = {
            'response': [
                {
                    'hostName': 'test-switch',
                    'ipAddress': '10.1.1.100',
                    'fabricName': 'test-fabric'
                }
            ]
        }

        task_args = {
            'parent_fabric_name': parent_fabric_name,
            'model_data_overlay': model_data_overlay
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_inventory_response

            result = action_module.run()

            # Verify mapping behavior
            msd_switches = result['msd_switches']
            self.assertEqual(msd_switches['test-switch'], '10.1.1.100')
            self.assertEqual(msd_switches['10.1.1.100'], '10.1.1.100')
            self.assertEqual(msd_switches['test-fabric'], 'test-fabric')

    def test_run_vrf_attach_switch_not_found(self):
        """Test run when VRF attach switch is not found in inventory."""
        parent_fabric_name = "msd-fabric"
        model_data_overlay = {
            'vrf_attach_switches_list': ['missing-switch'],
            'network_attach_switches_list': []
        }

        mock_inventory_response = {
            'response': [
                {
                    'hostName': 'existing-switch',
                    'ipAddress': '10.1.1.1',
                    'fabricName': 'child-fabric1'
                }
            ]
        }

        task_args = {
            'parent_fabric_name': parent_fabric_name,
            'model_data_overlay': model_data_overlay
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_inventory_response

            result = action_module.run()

            self.assertTrue(result['failed'])
            self.assertIn('msg', result)
            self.assertIn('missing-switch', result['msg'][0])

    def test_run_network_attach_switch_not_found(self):
        """Test run when network attach switch is not found in inventory."""
        parent_fabric_name = "msd-fabric"
        model_data_overlay = {
            'vrf_attach_switches_list': [],
            'network_attach_switches_list': ['missing-network-switch']
        }

        mock_inventory_response = {
            'response': [
                {
                    'hostName': 'existing-switch',
                    'ipAddress': '10.1.1.1',
                    'fabricName': 'child-fabric1'
                }
            ]
        }

        task_args = {
            'parent_fabric_name': parent_fabric_name,
            'model_data_overlay': model_data_overlay
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_inventory_response

            result = action_module.run()

            self.assertTrue(result['failed'])
            self.assertIn('msg', result)
            self.assertIn('missing-network-switch', result['msg'][0])

    def test_run_multiple_missing_switches(self):
        """Test run with multiple missing switches."""
        parent_fabric_name = "msd-fabric"
        model_data_overlay = {
            'vrf_attach_switches_list': ['missing-vrf-switch'],
            'network_attach_switches_list': ['missing-network-switch']
        }

        # Need at least one switch in inventory for the plugin to check
        mock_inventory_response = {
            'response': [
                {
                    'hostName': 'existing-switch',
                    'ipAddress': '10.1.1.1',
                    'fabricName': 'child-fabric1'
                }
            ]
        }

        task_args = {
            'parent_fabric_name': parent_fabric_name,
            'model_data_overlay': model_data_overlay
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_inventory_response

            result = action_module.run()

            self.assertTrue(result['failed'])
            self.assertEqual(len(result['msg']), 2)

    def test_run_empty_inventory_response(self):
        """Test run with empty inventory response."""
        parent_fabric_name = "msd-fabric"
        model_data_overlay = {
            'vrf_attach_switches_list': [],
            'network_attach_switches_list': []
        }

        mock_inventory_response = {
            'response': []
        }

        task_args = {
            'parent_fabric_name': parent_fabric_name,
            'model_data_overlay': model_data_overlay
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_inventory_response

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertEqual(result['msd_switches'], {})

    def test_run_switch_not_part_of_fabric_string_response(self):
        """Test run when response is string indicating switch not part of fabric."""
        parent_fabric_name = "msd-fabric"
        model_data_overlay = {
            'vrf_attach_switches_list': [],
            'network_attach_switches_list': []
        }

        mock_inventory_response = {
            'response': 'The queried switch is not part of the fabric configured'
        }

        task_args = {
            'parent_fabric_name': parent_fabric_name,
            'model_data_overlay': model_data_overlay
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_inventory_response

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertEqual(result['msd_switches'], {})

    def test_run_missing_response_key(self):
        """Test run when response key is missing."""
        parent_fabric_name = "msd-fabric"
        model_data_overlay = {
            'vrf_attach_switches_list': [],
            'network_attach_switches_list': []
        }

        mock_inventory_response = {}

        task_args = {
            'parent_fabric_name': parent_fabric_name,
            'model_data_overlay': model_data_overlay
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_inventory_response

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertEqual(result['msd_switches'], {})

    def test_run_empty_attach_lists(self):
        """Test run with empty attach lists."""
        parent_fabric_name = "msd-fabric"
        model_data_overlay = {
            'vrf_attach_switches_list': [],
            'network_attach_switches_list': []
        }

        mock_inventory_response = {
            'response': [
                {
                    'hostName': 'switch1',
                    'ipAddress': '10.1.1.1',
                    'fabricName': 'child-fabric1'
                }
            ]
        }

        task_args = {
            'parent_fabric_name': parent_fabric_name,
            'model_data_overlay': model_data_overlay
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_inventory_response

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertIn('msd_switches', result)
            self.assertEqual(result['msd_switches']['switch1'], '10.1.1.1')

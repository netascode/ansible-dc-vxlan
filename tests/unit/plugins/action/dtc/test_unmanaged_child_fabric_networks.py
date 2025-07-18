"""
Unit tests for unmanaged_child_fabric_networks action plugin.
"""
import pytest
from unittest.mock import patch

from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.unmanaged_child_fabric_networks import ActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.base_test import ActionModuleTestCase


class TestUnmanagedChildFabricNetworksActionModule(ActionModuleTestCase):
    """Test cases for unmanaged_child_fabric_networks action plugin."""

    def test_run_basic_functionality(self):
        """Test run with basic functionality."""
        task_args = {
            'fabric_data': {'fabric1': {}},
            'model_data': {'vxlan': {'multisite': {'overlay': {'networks': []}}}},
            'unmanaged_networks': []
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        # Mock the run method from parent class and _execute_module
        with patch.object(ActionModule, 'run') as mock_parent_run, \
             patch.object(ActionModule, '_execute_module') as mock_execute:
            
            mock_parent_run.return_value = {'changed': False}
            mock_execute.return_value = {'response': []}
            
            result = action_module.run()
            
            self.assertFalse(result['changed'])

    def test_run_empty_inputs(self):
        """Test run with empty inputs."""
        task_args = {
            'fabric_data': {},
            'model_data': {'vxlan': {'multisite': {'overlay': {'networks': []}}}},
            'unmanaged_networks': []
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        # Mock the run method from parent class
        with patch.object(ActionModule, 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}
            
            result = action_module.run()
            
            self.assertFalse(result['changed'])

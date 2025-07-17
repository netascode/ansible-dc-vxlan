"""
Unit tests for get_poap_data action plugin.
"""
import unittest
from unittest.mock import MagicMock, patch, PropertyMock
import re

from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.get_poap_data import ActionModule, POAPDevice
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.base_test import ActionModuleTestCase


class TestPOAPDevice(unittest.TestCase):
    """Test cases for POAPDevice class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_execute_module = MagicMock()
        self.mock_task_vars = {}
        self.mock_tmp = '/tmp'
        
        self.params = {
            'model_data': {
                'fabric': 'test_fabric',
                'topology': {
                    'switches': [
                        {
                            'name': 'switch1',
                            'management': {'ip': '192.168.1.1'},
                            'role': 'leaf',
                            'poap': {'bootstrap': True}
                        },
                        {
                            'name': 'switch2',
                            'management': {'ip': '192.168.1.2'},
                            'role': 'spine',
                            'poap': {'bootstrap': False}
                        }
                    ]
                }
            },
            'action_plugin': self.mock_execute_module,
            'task_vars': self.mock_task_vars,
            'tmp': self.mock_tmp
        }

    def test_init_with_valid_params(self):
        """Test POAPDevice initialization with valid parameters."""
        device = POAPDevice(self.params)
        
        self.assertEqual(device.fabric_name, 'test_fabric')
        self.assertEqual(len(device.switches), 2)
        self.assertEqual(device.switches[0]['name'], 'switch1')
        self.assertEqual(device.switches[1]['name'], 'switch2')
        self.assertEqual(device.execute_module, self.mock_execute_module)
        self.assertEqual(device.task_vars, self.mock_task_vars)
        self.assertEqual(device.tmp, self.mock_tmp)

    def test_init_missing_fabric(self):
        """Test POAPDevice initialization with missing fabric."""
        params = self.params.copy()
        del params['model_data']['fabric']
        
        with self.assertRaises(KeyError):
            POAPDevice(params)

    def test_init_missing_switches(self):
        """Test POAPDevice initialization with missing switches."""
        params = self.params.copy()
        del params['model_data']['topology']['switches']
        
        with self.assertRaises(KeyError):
            POAPDevice(params)

    def test_check_poap_supported_switches_with_poap_enabled(self):
        """Test check_poap_supported_switches with POAP enabled switches."""
        device = POAPDevice(self.params)
        device.check_poap_supported_switches()
        
        self.assertTrue(device.poap_supported_switches)

    def test_check_poap_supported_switches_no_poap_enabled(self):
        """Test check_poap_supported_switches with no POAP enabled switches."""
        params = self.params.copy()
        for switch in params['model_data']['topology']['switches']:
            if 'poap' in switch:
                switch['poap']['bootstrap'] = False
        
        device = POAPDevice(params)
        device.check_poap_supported_switches()
        
        self.assertFalse(device.poap_supported_switches)

    def test_check_poap_supported_switches_no_poap_key(self):
        """Test check_poap_supported_switches with no poap key."""
        params = self.params.copy()
        for switch in params['model_data']['topology']['switches']:
            if 'poap' in switch:
                del switch['poap']
        
        device = POAPDevice(params)
        device.check_poap_supported_switches()
        
        self.assertFalse(device.poap_supported_switches)

    def test_check_preprovision_supported_switches_with_preprovision(self):
        """Test check_preprovision_supported_switches with preprovision enabled."""
        params = self.params.copy()
        params['model_data']['topology']['switches'][0]['poap']['preprovision'] = True
        
        device = POAPDevice(params)
        device.check_preprovision_supported_switches()
        
        self.assertTrue(device.preprovision_supported_switches)

    def test_check_preprovision_supported_switches_no_preprovision(self):
        """Test check_preprovision_supported_switches with no preprovision."""
        device = POAPDevice(self.params)
        device.check_preprovision_supported_switches()
        
        self.assertFalse(device.preprovision_supported_switches)

    def test_refresh_discovered_successful(self):
        """Test refresh_discovered with successful response."""
        mock_response = {
            'response': [
                {
                    'ipAddress': '192.168.1.1',
                    'switchRole': 'leaf',
                    'logicalName': 'switch1'
                }
            ]
        }
        
        self.mock_execute_module.return_value = mock_response
        
        device = POAPDevice(self.params)
        device.refresh_discovered()
        
        self.assertEqual(device.discovered_switch_data, mock_response['response'])
        self.mock_execute_module.assert_called_once_with(
            module_name="cisco.dcnm.dcnm_inventory",
            module_args={
                "fabric": "test_fabric",
                "state": "query",
            },
            task_vars=self.mock_task_vars,
            tmp=self.mock_tmp
        )

    def test_refresh_discovered_empty_response(self):
        """Test refresh_discovered with empty response."""
        mock_response = {
            'response': []
        }
        
        self.mock_execute_module.return_value = mock_response
        
        device = POAPDevice(self.params)
        device.refresh_discovered()
        
        self.assertEqual(device.discovered_switch_data, [])

    def test_refresh_discovered_no_response(self):
        """Test refresh_discovered with no response."""
        mock_response = {}
        
        self.mock_execute_module.return_value = mock_response
        
        device = POAPDevice(self.params)
        device.refresh_discovered()
        
        self.assertEqual(device.discovered_switch_data, [])

    def test_get_discovered_found(self):
        """Test _get_discovered when device is found."""
        device = POAPDevice(self.params)
        device.discovered_switch_data = [
            {
                'ipAddress': '192.168.1.1',
                'switchRole': 'leaf',
                'logicalName': 'switch1'
            }
        ]
        
        result = device._get_discovered('192.168.1.1', 'leaf', 'switch1')
        
        self.assertTrue(result)

    def test_get_discovered_not_found(self):
        """Test _get_discovered when device is not found."""
        device = POAPDevice(self.params)
        device.discovered_switch_data = [
            {
                'ipAddress': '192.168.1.1',
                'switchRole': 'leaf',
                'logicalName': 'switch1'
            }
        ]
        
        result = device._get_discovered('192.168.1.2', 'spine', 'switch2')
        
        self.assertFalse(result)

    def test_get_discovered_partial_match(self):
        """Test _get_discovered with partial match."""
        device = POAPDevice(self.params)
        device.discovered_switch_data = [
            {
                'ipAddress': '192.168.1.1',
                'switchRole': 'leaf',
                'logicalName': 'switch1'
            }
        ]
        
        # IP matches but role doesn't
        result = device._get_discovered('192.168.1.1', 'spine', 'switch1')
        self.assertFalse(result)
        
        # IP and role match but hostname doesn't
        result = device._get_discovered('192.168.1.1', 'leaf', 'switch2')
        self.assertFalse(result)


class TestGetPoapDataActionModule(ActionModuleTestCase):
    """Test cases for get_poap_data action plugin."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.action_module = self.create_action_module(ActionModule)

    def test_run_no_poap_supported_switches(self):
        """Test run when no switches support POAP."""
        model_data = {
            'fabric': 'test_fabric',
            'topology': {
                'switches': [
                    {
                        'name': 'switch1',
                        'management': {'ip': '192.168.1.1'},
                        'role': 'leaf'
                        # No poap configuration
                    }
                ]
            }
        }
        
        task_args = {
            'model_data': model_data
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}
            
            result = action_module.run()
            
            self.assertFalse(result['failed'])
            self.assertEqual(result['poap_data'], {})

    @patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.get_poap_data.POAPDevice')
    def test_run_poap_supported_refresh_successful(self, mock_poap_device):
        """Test run when POAP is supported and refresh is successful."""
        model_data = {
            'fabric': 'test_fabric',
            'topology': {
                'switches': [
                    {
                        'name': 'switch1',
                        'management': {'ip': '192.168.1.1'},
                        'role': 'leaf',
                        'poap': {'bootstrap': True}
                    }
                ]
            }
        }
        
        task_args = {
            'model_data': model_data
        }
        
        # Mock POAPDevice instance
        mock_workflow = MagicMock()
        mock_workflow.poap_supported_switches = True
        mock_workflow.refresh_succeeded = True
        mock_workflow.poap_data = {'switch1': {'serial': '12345'}}
        mock_poap_device.return_value = mock_workflow
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}
            
            result = action_module.run()
            
            self.assertFalse(result['failed'])
            self.assertEqual(result['poap_data'], {'switch1': {'serial': '12345'}})
            mock_workflow.refresh_discovered.assert_called_once()
            mock_workflow.check_poap_supported_switches.assert_called_once()
            mock_workflow.refresh.assert_called_once()

    @patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.get_poap_data.POAPDevice')
    def test_run_poap_supported_refresh_failed_dhcp_message(self, mock_poap_device):
        """Test run when POAP refresh fails with DHCP message."""
        model_data = {
            'fabric': 'test_fabric',
            'topology': {
                'switches': [
                    {
                        'name': 'switch1',
                        'management': {'ip': '192.168.1.1'},
                        'role': 'leaf',
                        'poap': {'bootstrap': True}
                    }
                ]
            }
        }
        
        task_args = {
            'model_data': model_data
        }
        
        # Mock POAPDevice instance
        mock_workflow = MagicMock()
        mock_workflow.poap_supported_switches = True
        mock_workflow.refresh_succeeded = False
        mock_workflow.refresh_message = "Please enable the DHCP in Fabric Settings to start the bootstrap"
        mock_workflow.poap_data = {}
        mock_poap_device.return_value = mock_workflow
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}
            
            result = action_module.run()
            
            self.assertFalse(result['failed'])
            self.assertEqual(result['poap_data'], {})

    @patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.get_poap_data.POAPDevice')
    def test_run_poap_supported_refresh_failed_invalid_fabric(self, mock_poap_device):
        """Test run when POAP refresh fails with invalid fabric message."""
        model_data = {
            'fabric': 'test_fabric',
            'topology': {
                'switches': [
                    {
                        'name': 'switch1',
                        'management': {'ip': '192.168.1.1'},
                        'role': 'leaf',
                        'poap': {'bootstrap': True}
                    }
                ]
            }
        }
        
        task_args = {
            'model_data': model_data
        }
        
        # Mock POAPDevice instance
        mock_workflow = MagicMock()
        mock_workflow.poap_supported_switches = True
        mock_workflow.refresh_succeeded = False
        mock_workflow.refresh_message = "Invalid Fabric"
        mock_workflow.poap_data = {}
        mock_poap_device.return_value = mock_workflow
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}
            
            result = action_module.run()
            
            self.assertFalse(result['failed'])
            self.assertEqual(result['poap_data'], {})

    @patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.get_poap_data.POAPDevice')
    def test_run_poap_supported_refresh_failed_unrecognized_error(self, mock_poap_device):
        """Test run when POAP refresh fails with unrecognized error."""
        model_data = {
            'fabric': 'test_fabric',
            'topology': {
                'switches': [
                    {
                        'name': 'switch1',
                        'management': {'ip': '192.168.1.1'},
                        'role': 'leaf',
                        'poap': {'bootstrap': True}
                    }
                ]
            }
        }
        
        task_args = {
            'model_data': model_data
        }
        
        # Mock POAPDevice instance
        mock_workflow = MagicMock()
        mock_workflow.poap_supported_switches = True
        mock_workflow.refresh_succeeded = False
        mock_workflow.refresh_message = "Unexpected error occurred"
        mock_workflow.poap_data = {}
        mock_poap_device.return_value = mock_workflow
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}
            
            result = action_module.run()
            
            self.assertTrue(result['failed'])
            self.assertIn("Unrecognized Failure Attempting To Get POAP Data", result['message'])

    @patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.get_poap_data.POAPDevice')
    def test_run_poap_supported_but_no_poap_data(self, mock_poap_device):
        """Test run when POAP is supported but no POAP data is available."""
        model_data = {
            'fabric': 'test_fabric',
            'topology': {
                'switches': [
                    {
                        'name': 'switch1',
                        'management': {'ip': '192.168.1.1'},
                        'role': 'leaf',
                        'poap': {'bootstrap': True}
                    }
                ]
            }
        }
        
        task_args = {
            'model_data': model_data
        }
        
        # Mock POAPDevice instance
        mock_workflow = MagicMock()
        mock_workflow.poap_supported_switches = True
        mock_workflow.refresh_succeeded = True
        mock_workflow.poap_data = {}
        mock_poap_device.return_value = mock_workflow
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}
            
            result = action_module.run()
            
            self.assertTrue(result['failed'])
            self.assertIn("POAP is enabled on at least one switch", result['message'])
            self.assertIn("POAP bootstrap data is not yet available", result['message'])


if __name__ == '__main__':
    unittest.main()

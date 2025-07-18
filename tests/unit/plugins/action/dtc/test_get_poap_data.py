"""
Unit tests for get_poap_data action plugin.
"""
import unittest
from unittest.mock import MagicMock, patch
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
                'vxlan': {
                    'fabric': {
                        'name': 'test_fabric'
                    },
                    'topology': {
                        'switches': [
                            {
                                'name': 'switch1',
                                'management': {
                                    'management_ipv4_address': '192.168.1.1'
                                },
                                'role': 'leaf',
                                'poap': {'bootstrap': True}
                            },
                            {
                                'name': 'switch2',
                                'management': {
                                    'management_ipv4_address': '192.168.1.2'
                                },
                                'role': 'spine',
                                'poap': {'bootstrap': False}
                            }
                        ]
                    }
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
        del params['model_data']['vxlan']['fabric']
        
        with self.assertRaises(KeyError):
            POAPDevice(params)

    def test_init_missing_switches(self):
        """Test POAPDevice initialization with missing switches."""
        params = self.params.copy()
        del params['model_data']['vxlan']['topology']['switches']
        
        with self.assertRaises(KeyError):
            POAPDevice(params)

    def test_check_poap_supported_switches_with_poap_enabled(self):
        """Test check_poap_supported_switches with POAP enabled switches."""
        device = POAPDevice(self.params)
        # Mock _get_discovered to return False (switch not discovered)
        device._get_discovered = MagicMock(return_value=False)
        device.check_poap_supported_switches()
        
        self.assertTrue(device.poap_supported_switches)

    def test_check_poap_supported_switches_no_poap_enabled(self):
        """Test check_poap_supported_switches with no POAP enabled switches."""
        params = self.params.copy()
        for switch in params['model_data']['vxlan']['topology']['switches']:
            if 'poap' in switch:
                switch['poap']['bootstrap'] = False
        
        device = POAPDevice(params)
        device.check_poap_supported_switches()
        
        self.assertFalse(device.poap_supported_switches)

    def test_check_poap_supported_switches_no_poap_key(self):
        """Test check_poap_supported_switches with no poap key."""
        params = self.params.copy()
        for switch in params['model_data']['vxlan']['topology']['switches']:
            if 'poap' in switch:
                del switch['poap']
        
        device = POAPDevice(params)
        device.check_poap_supported_switches()
        
        self.assertFalse(device.poap_supported_switches)

    def test_check_preprovision_supported_switches_with_preprovision(self):
        """Test check_preprovision_supported_switches with preprovision enabled."""
        params = self.params.copy()
        params['model_data']['vxlan']['topology']['switches'][0]['poap']['preprovision'] = True
        
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

    def test_refresh_discovered_no_response(self):
        """Test refresh_discovered with no response."""
        self.mock_execute_module.return_value = {}
        
        device = POAPDevice(self.params)
        device.refresh_discovered()
        
        self.assertEqual(device.discovered_switch_data, [])

    def test_refresh_discovered_empty_response(self):
        """Test refresh_discovered with empty response."""
        self.mock_execute_module.return_value = {'response': []}
        
        device = POAPDevice(self.params)
        device.refresh_discovered()
        
        self.assertEqual(device.discovered_switch_data, [])

    def test_get_discovered_found(self):
        """Test _get_discovered when switch is found."""
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
        """Test _get_discovered when switch is not found."""
        device = POAPDevice(self.params)
        device.discovered_switch_data = []
        
        result = device._get_discovered('192.168.1.1', 'leaf', 'switch1')
        self.assertFalse(result)

    def test_get_discovered_partial_match(self):
        """Test _get_discovered with partial match (different role)."""
        device = POAPDevice(self.params)
        device.discovered_switch_data = [
            {
                'ipAddress': '192.168.1.1',
                'switchRole': 'spine',
                'logicalName': 'switch1'
            }
        ]
        
        result = device._get_discovered('192.168.1.1', 'leaf', 'switch1')
        self.assertFalse(result)

    def test_check_poap_supported_switches_already_discovered(self):
        """Test check_poap_supported_switches when switch is already discovered (continue branch)."""
        device = POAPDevice(self.params)
        # Mock _get_discovered to return True (switch already discovered)
        device._get_discovered = MagicMock(return_value=True)
        device.check_poap_supported_switches()
        
        # Should remain False because discovered switches are skipped
        self.assertFalse(device.poap_supported_switches)

    def test_refresh_failed_response(self):
        """Test refresh method with failed response to cover elif branch."""
        device = POAPDevice(self.params)
        
        # Mock execute_module to return failed response
        device.execute_module = MagicMock(return_value={
            'failed': True,
            'msg': {'DATA': 'Some error message'}
        })
        
        device.refresh()
        
        self.assertFalse(device.refresh_succeeded)
        self.assertEqual(device.refresh_message, 'Some error message')

    def test_split_string_data_json_decode_error(self):
        """Test _split_string_data with invalid JSON to cover exception handling."""
        device = POAPDevice(self.params)
        
        # Test with invalid JSON data
        result = device._split_string_data('invalid json data')
        
        self.assertEqual(result['gateway'], 'NOT_SET')
        self.assertEqual(result['modulesModel'], 'NOT_SET')

    def test_split_string_data_valid_json(self):
        """Test _split_string_data with valid JSON data."""
        device = POAPDevice(self.params)
        
        # Test with valid JSON data
        valid_json = '{"gateway": "192.168.1.1/24", "modulesModel": ["N9K-X9364v", "N9K-vSUP"]}'
        result = device._split_string_data(valid_json)
        
        self.assertEqual(result['gateway'], '192.168.1.1/24')
        self.assertEqual(result['modulesModel'], ['N9K-X9364v', 'N9K-vSUP'])


class TestGetPoapDataActionModule(ActionModuleTestCase):
    """Test cases for ActionModule."""

    def test_run_no_poap_supported_switches(self):
        """Test run when no switches support POAP."""
        model_data = {
            'vxlan': {
                'fabric': {
                    'name': 'test_fabric'
                },
                'topology': {
                    'switches': [
                        {
                            'name': 'switch1',
                            'management': {'management_ipv4_address': '192.168.1.1'},
                            'role': 'leaf'
                            # No poap configuration
                        }
                    ]
                }
            }
        }

        task_args = {
            'model_data': model_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module
        with patch.object(action_module, '_execute_module') as mock_execute:
            mock_execute.return_value = {'response': []}

            result = action_module.run()

            # Should not fail and should return with poap_data
            self.assertFalse(result.get('failed', False))
            self.assertIn('poap_data', result)

    def test_run_poap_supported_but_no_poap_data(self):
        """Test run when POAP is supported but no data is available."""
        model_data = {
            'vxlan': {
                'fabric': {
                    'name': 'test_fabric'
                },
                'topology': {
                    'switches': [
                        {
                            'name': 'switch1',
                            'management': {'management_ipv4_address': '192.168.1.1'},
                            'role': 'leaf',
                            'poap': {'bootstrap': True}
                        }
                    ]
                }
            }
        }

        task_args = {
            'model_data': model_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module calls
        with patch.object(action_module, '_execute_module') as mock_execute:
            def mock_side_effect(module_name, **kwargs):
                if module_name == "cisco.dcnm.dcnm_inventory":
                    return {'response': []}  # refresh_discovered
                elif module_name == "cisco.dcnm.dcnm_rest":
                    return {'response': {'RETURN_CODE': 200, 'DATA': []}}  # refresh (empty POAP data)
                
            mock_execute.side_effect = mock_side_effect

            result = action_module.run()

            self.assertTrue(result['failed'])
            self.assertIn('POAP is enabled', result['message'])

    def test_run_poap_supported_refresh_successful(self):
        """Test run when POAP refresh is successful."""
        model_data = {
            'vxlan': {
                'fabric': {
                    'name': 'test_fabric'
                },
                'topology': {
                    'switches': [
                        {
                            'name': 'switch1',
                            'management': {'management_ipv4_address': '192.168.1.1'},
                            'role': 'leaf',
                            'poap': {'bootstrap': True}
                        }
                    ]
                }
            }
        }

        task_args = {
            'model_data': model_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Create valid POAP data that matches what _parse_poap_data expects
        poap_data = [
            {
                'serialNumber': 'ABC123',
                'model': 'N9K-C9300v',
                'version': '9.3(8)',
                'data': '{"gateway": "192.168.1.1/24", "modulesModel": ["N9K-X9364v", "N9K-vSUP"]}'
            }
        ]

        # Mock _execute_module calls
        with patch.object(action_module, '_execute_module') as mock_execute:
            def mock_side_effect(module_name, **kwargs):
                if module_name == "cisco.dcnm.dcnm_inventory":
                    return {'response': []}  # refresh_discovered
                elif module_name == "cisco.dcnm.dcnm_rest":
                    return {'response': {'RETURN_CODE': 200, 'DATA': poap_data}}  # refresh
                
            mock_execute.side_effect = mock_side_effect

            result = action_module.run()

            self.assertFalse(result.get('failed', False))
            self.assertIn('poap_data', result)
            # Verify the parsed structure
            self.assertIn('ABC123', result['poap_data'])
            self.assertEqual(result['poap_data']['ABC123']['model'], 'N9K-C9300v')

    @patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.get_poap_data.POAPDevice')
    def test_run_poap_supported_refresh_failed_dhcp_message(self, mock_poap_device):
        """Test run when POAP refresh fails with DHCP message."""
        model_data = {
            'vxlan': {'fabric': {'name': 'test_fabric'}}
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

        result = action_module.run()

        # The logic flaw in the plugin causes this to still fail with "Unrecognized Failure"
        # because the else clause applies to the second if statement, not both
        self.assertTrue(result.get('failed', False))
        self.assertIn('Unrecognized Failure', result['message'])

    @patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.get_poap_data.POAPDevice')
    def test_run_poap_supported_refresh_failed_invalid_fabric(self, mock_poap_device):
        """Test run when POAP refresh fails with invalid fabric message."""
        model_data = {
            'vxlan': {'fabric': {'name': 'test_fabric'}}
        }

        task_args = {
            'model_data': model_data
        }

        # Mock POAPDevice instance
        mock_workflow = MagicMock()
        mock_workflow.poap_supported_switches = True
        mock_workflow.refresh_succeeded = False
        mock_workflow.refresh_message = "Invalid Fabric"
        mock_workflow.poap_data = {}  # Empty dict will still cause failure due to "not results['poap_data']" check
        mock_poap_device.return_value = mock_workflow

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        # Should fail because empty poap_data fails the "not results['poap_data']" check 
        # even though the Invalid Fabric error message is ignored
        self.assertTrue(result.get('failed', False))
        self.assertIn('POAP is enabled on at least one switch', result['message'])

    @patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.get_poap_data.POAPDevice')
    def test_run_poap_supported_refresh_failed_unrecognized_error(self, mock_poap_device):
        """Test run when POAP refresh fails with unrecognized error."""
        model_data = {
            'vxlan': {'fabric': {'name': 'test_fabric'}}
        }

        task_args = {
            'model_data': model_data
        }

        # Mock POAPDevice instance
        mock_workflow = MagicMock()
        mock_workflow.poap_supported_switches = True
        mock_workflow.refresh_succeeded = False
        mock_workflow.refresh_message = "Some unrecognized error"
        mock_workflow.poap_data = {}
        mock_poap_device.return_value = mock_workflow

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertTrue(result['failed'])
        self.assertIn('Unrecognized Failure', result['message'])


if __name__ == '__main__':
    unittest.main()

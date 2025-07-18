"""
Unit tests for update_switch_hostname_policy action plugin.
"""
import pytest
from unittest.mock import patch

from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.update_switch_hostname_policy import ActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.base_test import ActionModuleTestCase


class TestUpdateSwitchHostnamePolicyActionModule(ActionModuleTestCase):
    """Test cases for update_switch_hostname_policy action plugin."""

    def test_run_hostname_needs_update(self):
        """Test run when hostname needs to be updated."""
        model_data = {
            'vxlan': {
                'fabric': {
                    'type': 'VXLAN_EVPN'
                },
                'topology': {
                    'switches': [
                        {
                            'serial_number': 'ABC123',
                            'name': 'new-switch-name'
                        }
                    ]
                }
            }
        }
        
        switch_serial_numbers = ['ABC123']
        template_name = 'switch_freeform'
        
        mock_policy = {
            'nvPairs': {
                'SWITCH_NAME': 'old-switch-name'
            },
            'templateName': 'switch_freeform',
            'serialNumber': 'ABC123'
        }
        
        task_args = {
            'model_data': model_data,
            'switch_serial_numbers': switch_serial_numbers,
            'template_name': template_name
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        # Only mock the helper function, not the parent run()
        with patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.update_switch_hostname_policy.ndfc_get_switch_policy_using_template') as mock_helper:
            mock_helper.return_value = mock_policy
            
            result = action_module.run()
            
            self.assertTrue(result['changed'])
            self.assertIn('policy_update', result)
            self.assertIn('ABC123', result['policy_update'])
            self.assertEqual(result['policy_update']['ABC123']['nvPairs']['SWITCH_NAME'], 'new-switch-name')

    def test_run_hostname_no_update_needed(self):
        """Test run when hostname is already correct."""
        model_data = {
            'vxlan': {
                'fabric': {
                    'type': 'VXLAN_EVPN'
                },
                'topology': {
                    'switches': [
                        {
                            'serial_number': 'ABC123',
                            'name': 'correct-switch-name'
                        }
                    ]
                }
            }
        }
        
        switch_serial_numbers = ['ABC123']
        template_name = 'switch_freeform'
        
        mock_policy = {
            'nvPairs': {
                'SWITCH_NAME': 'correct-switch-name'  # Already matches
            },
            'templateName': 'switch_freeform',
            'serialNumber': 'ABC123'
        }
        
        task_args = {
            'model_data': model_data,
            'switch_serial_numbers': switch_serial_numbers,
            'template_name': template_name
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        with patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.update_switch_hostname_policy.ndfc_get_switch_policy_using_template') as mock_helper:
            mock_helper.return_value = mock_policy
            
            result = action_module.run()
            
            self.assertFalse(result['changed'])
            self.assertIn('policy_update', result)
            self.assertEqual(result['policy_update'], {})

    def test_run_multiple_switches_mixed_updates(self):
        """Test run with multiple switches, some needing updates."""
        model_data = {
            'vxlan': {
                'fabric': {
                    'type': 'VXLAN_EVPN'
                },
                'topology': {
                    'switches': [
                        {
                            'serial_number': 'ABC123',
                            'name': 'new-name-1'
                        },
                        {
                            'serial_number': 'DEF456',
                            'name': 'correct-name-2'
                        }
                    ]
                }
            }
        }
        
        switch_serial_numbers = ['ABC123', 'DEF456']
        template_name = 'switch_freeform'
        
        def mock_helper_side_effect(self, task_vars, tmp, switch_serial_number, template_name):
            if switch_serial_number == 'ABC123':
                return {
                    'nvPairs': {'SWITCH_NAME': 'old-name-1'},
                    'templateName': 'switch_freeform',
                    'serialNumber': 'ABC123'
                }
            else:  # DEF456
                return {
                    'nvPairs': {'SWITCH_NAME': 'correct-name-2'},
                    'templateName': 'switch_freeform',
                    'serialNumber': 'DEF456'
                }
        
        task_args = {
            'model_data': model_data,
            'switch_serial_numbers': switch_serial_numbers,
            'template_name': template_name
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        with patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.update_switch_hostname_policy.ndfc_get_switch_policy_using_template') as mock_helper:
            mock_helper.side_effect = mock_helper_side_effect
            
            result = action_module.run()
            
            self.assertTrue(result['changed'])
            # Should have only one switch needing update
            self.assertEqual(len(result['policy_update']), 1)
            self.assertIn('ABC123', result['policy_update'])
            self.assertNotIn('DEF456', result['policy_update'])

    def test_run_external_fabric_type(self):
        """Test run with External fabric type."""
        model_data = {
            'vxlan': {
                'fabric': {
                    'type': 'External'
                },
                'topology': {
                    'switches': [
                        {
                            'serial_number': 'ABC123',
                            'name': 'external-switch'
                        }
                    ]
                }
            }
        }
        
        switch_serial_numbers = ['ABC123']
        template_name = 'switch_freeform'
        
        mock_policy = {
            'nvPairs': {
                'SWITCH_NAME': 'old-external-switch'
            },
            'templateName': 'switch_freeform',
            'serialNumber': 'ABC123'
        }
        
        task_args = {
            'model_data': model_data,
            'switch_serial_numbers': switch_serial_numbers,
            'template_name': template_name
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        with patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.update_switch_hostname_policy.ndfc_get_switch_policy_using_template') as mock_helper:
            mock_helper.return_value = mock_policy
            
            result = action_module.run()
            
            self.assertTrue(result['changed'])
            self.assertIn('ABC123', result['policy_update'])

    def test_run_isn_fabric_type(self):
        """Test run with ISN fabric type."""
        model_data = {
            'vxlan': {
                'fabric': {
                    'type': 'ISN'
                },
                'topology': {
                    'switches': [
                        {
                            'serial_number': 'ABC123',
                            'name': 'isn-switch'
                        }
                    ]
                }
            }
        }
        
        switch_serial_numbers = ['ABC123']
        template_name = 'switch_freeform'
        
        mock_policy = {
            'nvPairs': {
                'SWITCH_NAME': 'old-isn-switch'
            },
            'templateName': 'switch_freeform',
            'serialNumber': 'ABC123'
        }
        
        task_args = {
            'model_data': model_data,
            'switch_serial_numbers': switch_serial_numbers,
            'template_name': template_name
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        with patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.update_switch_hostname_policy.ndfc_get_switch_policy_using_template') as mock_helper:
            mock_helper.return_value = mock_policy
            
            result = action_module.run()
            
            self.assertTrue(result['changed'])
            self.assertIn('ABC123', result['policy_update'])

    def test_run_policy_update_triggers_changed(self):
        """Test run verifies that policy updates trigger changed flag."""
        model_data = {
            'vxlan': {
                'fabric': {
                    'type': 'VXLAN_EVPN'
                },
                'topology': {
                    'switches': [
                        {
                            'serial_number': 'ABC123',
                            'name': 'updated-name'
                        }
                    ]
                }
            }
        }
        
        switch_serial_numbers = ['ABC123']
        template_name = 'switch_freeform'
        
        mock_policy = {
            'nvPairs': {
                'SWITCH_NAME': 'original-name'
            },
            'templateName': 'switch_freeform',
            'serialNumber': 'ABC123'
        }
        
        task_args = {
            'model_data': model_data,
            'switch_serial_numbers': switch_serial_numbers,
            'template_name': template_name
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        with patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.update_switch_hostname_policy.ndfc_get_switch_policy_using_template') as mock_helper:
            mock_helper.return_value = mock_policy
            
            result = action_module.run()
            
            self.assertTrue(result['changed'])
            self.assertTrue(len(result['policy_update']) > 0)

    def test_run_empty_switch_serial_numbers(self):
        """Test run with empty switch serial numbers list."""
        model_data = {
            'vxlan': {
                'fabric': {
                    'type': 'VXLAN_EVPN'
                },
                'topology': {
                    'switches': []
                }
            }
        }
        
        switch_serial_numbers = []
        template_name = 'switch_freeform'
        
        task_args = {
            'model_data': model_data,
            'switch_serial_numbers': switch_serial_numbers,
            'template_name': template_name
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        result = action_module.run()
        
        self.assertFalse(result['changed'])
        self.assertIn('policy_update', result)
        self.assertEqual(result['policy_update'], {})

    def test_run_switch_not_found_in_model(self):
        """Test run when switch is not found in data model."""
        model_data = {
            'vxlan': {
                'fabric': {
                    'type': 'VXLAN_EVPN'
                },
                'topology': {
                    'switches': [
                        {
                            'serial_number': 'ABC123',
                            'name': 'existing-switch'
                        }
                    ]
                }
            }
        }
        
        switch_serial_numbers = ['XYZ999']  # Not in model
        template_name = 'switch_freeform'
        
        mock_policy = {
            'nvPairs': {
                'SWITCH_NAME': 'some-name'
            },
            'templateName': 'switch_freeform',
            'serialNumber': 'XYZ999'
        }
        
        task_args = {
            'model_data': model_data,
            'switch_serial_numbers': switch_serial_numbers,
            'template_name': template_name
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        with patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.update_switch_hostname_policy.ndfc_get_switch_policy_using_template') as mock_helper:
            mock_helper.return_value = mock_policy
            
            # Should raise StopIteration when switch not found
            with self.assertRaises(StopIteration):
                result = action_module.run()

    def test_run_unsupported_fabric_type(self):
        """Test run with unsupported fabric type."""
        model_data = {
            'vxlan': {
                'fabric': {
                    'type': 'UNSUPPORTED_TYPE'
                },
                'topology': {
                    'switches': []
                }
            }
        }
        
        switch_serial_numbers = ['ABC123']
        template_name = 'switch_freeform'
        
        mock_policy = {
            'nvPairs': {
                'SWITCH_NAME': 'some-name'
            },
            'templateName': 'switch_freeform',
            'serialNumber': 'ABC123'
        }
        
        task_args = {
            'model_data': model_data,
            'switch_serial_numbers': switch_serial_numbers,
            'template_name': template_name
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        with patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.update_switch_hostname_policy.ndfc_get_switch_policy_using_template') as mock_helper:
            mock_helper.return_value = mock_policy
            
            # Should raise StopIteration when fabric type doesn't match supported types
            with self.assertRaises(StopIteration):
                result = action_module.run()

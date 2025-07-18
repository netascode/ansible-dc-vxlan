"""
Unit tests for vpc_pair_check action plugin.
"""
import unittest
from unittest.mock import MagicMock, patch

from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.vpc_pair_check import ActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.base_test import ActionModuleTestCase


class TestVpcPairCheckActionModule(ActionModuleTestCase):
    """Test cases for vpc_pair_check action plugin."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.action_module = self.create_action_module(ActionModule)

    def test_run_valid_vpc_data_all_configured(self):
        """Test run with valid VPC data where all switches are configured."""
        vpc_data = {
            'results': [
                {
                    'response': [
                        {
                            'hostName': 'switch1',
                            'isVpcConfigured': True
                        },
                        {
                            'hostName': 'switch2',
                            'isVpcConfigured': True
                        }
                    ]
                },
                {
                    'response': [
                        {
                            'hostName': 'switch3',
                            'isVpcConfigured': True
                        },
                        {
                            'hostName': 'switch4',
                            'isVpcConfigured': True
                        }
                    ]
                }
            ]
        }

        task_args = {
            'vpc_data': vpc_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)

    def test_run_valid_vpc_data_some_not_configured(self):
        """Test run with valid VPC data where some switches are not configured."""
        vpc_data = {
            'results': [
                {
                    'response': [
                        {
                            'hostName': 'switch1',
                            'isVpcConfigured': False
                        },
                        {
                            'hostName': 'switch2',
                            'isVpcConfigured': True
                        }
                    ]
                },
                {
                    'response': [
                        {
                            'hostName': 'switch3',
                            'isVpcConfigured': False
                        },
                        {
                            'hostName': 'switch4',
                            'isVpcConfigured': False
                        }
                    ]
                }
            ]
        }

        task_args = {
            'vpc_data': vpc_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)

    def test_run_single_vpc_pair(self):
        """Test run with single VPC pair."""
        vpc_data = {
            'results': [
                {
                    'response': [
                        {
                            'hostName': 'switch1',
                            'isVpcConfigured': True
                        },
                        {
                            'hostName': 'switch2',
                            'isVpcConfigured': False
                        }
                    ]
                }
            ]
        }

        task_args = {
            'vpc_data': vpc_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)

    def test_run_empty_vpc_data(self):
        """Test run with empty VPC data."""
        vpc_data = {
            'results': []
        }

        task_args = {
            'vpc_data': vpc_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)

    def test_run_empty_response_in_pair(self):
        """Test run with empty response in VPC pair."""
        vpc_data = {
            'results': [
                {
                    'response': []
                }
            ]
        }

        task_args = {
            'vpc_data': vpc_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)

    def test_run_single_switch_in_pair(self):
        """Test run with single switch in VPC pair."""
        vpc_data = {
            'results': [
                {
                    'response': [
                        {
                            'hostName': 'switch1',
                            'isVpcConfigured': False
                        }
                    ]
                }
            ]
        }

        task_args = {
            'vpc_data': vpc_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)

    def test_run_multiple_vpc_pairs_mixed_states(self):
        """Test run with multiple VPC pairs in mixed states."""
        vpc_data = {
            'results': [
                {
                    'response': [
                        {
                            'hostName': 'leaf1',
                            'isVpcConfigured': True
                        },
                        {
                            'hostName': 'leaf2',
                            'isVpcConfigured': True
                        }
                    ]
                },
                {
                    'response': [
                        {
                            'hostName': 'leaf3',
                            'isVpcConfigured': False
                        },
                        {
                            'hostName': 'leaf4',
                            'isVpcConfigured': False
                        }
                    ]
                },
                {
                    'response': [
                        {
                            'hostName': 'leaf5',
                            'isVpcConfigured': True
                        },
                        {
                            'hostName': 'leaf6',
                            'isVpcConfigured': False
                        }
                    ]
                }
            ]
        }

        task_args = {
            'vpc_data': vpc_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)

    def test_run_missing_hostname_key(self):
        """Test run with missing hostName key."""
        vpc_data = {
            'results': [
                {
                    'response': [
                        {
                            'isVpcConfigured': False
                            # Missing hostName key
                        }
                    ]
                }
            ]
        }

        task_args = {
            'vpc_data': vpc_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            with self.assertRaises(KeyError):
                action_module.run()

    def test_run_missing_is_vpc_configured_key(self):
        """Test run with missing isVpcConfigured key."""
        vpc_data = {
            'results': [
                {
                    'response': [
                        {
                            'hostName': 'switch1'
                        }
                    ]
                }
            ]
        }

        task_args = {
            'vpc_data': vpc_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            with self.assertRaises(KeyError):
                action_module.run()

    def test_run_missing_response_key(self):
        """Test run with missing response key."""
        vpc_data = {
            'results': [
                {
                    'other_key': 'value'
                }
            ]
        }

        task_args = {
            'vpc_data': vpc_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            with self.assertRaises(KeyError):
                action_module.run()

    def test_run_missing_results_key(self):
        """Test run with missing results key."""
        vpc_data = {
            'other_key': 'value'
        }

        task_args = {
            'vpc_data': vpc_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            with self.assertRaises(KeyError):
                action_module.run()

    def test_run_vpc_pairs_creation_logic(self):
        """Test the VPC pairs creation logic with specific data structure."""
        vpc_data = {
            'results': [
                {
                    'response': [
                        {
                            'hostName': 'netascode-rtp-leaf1',
                            'isVpcConfigured': False
                        },
                        {
                            'hostName': 'netascode-rtp-leaf2',
                            'isVpcConfigured': False
                        }
                    ]
                },
                {
                    'response': [
                        {
                            'hostName': 'netascode-rtp-leaf3',
                            'isVpcConfigured': False
                        },
                        {
                            'hostName': 'netascode-rtp-leaf4',
                            'isVpcConfigured': False
                        }
                    ]
                }
            ]
        }

        task_args = {
            'vpc_data': vpc_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)


if __name__ == '__main__':
    unittest.main()

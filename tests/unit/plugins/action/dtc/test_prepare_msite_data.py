"""
Unit tests for prepare_msite_data action plugin.
"""
import pytest
from unittest.mock import patch, MagicMock

from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.prepare_msite_data import ActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.base_test import ActionModuleTestCase


class TestPrepareMsiteDataActionModule(ActionModuleTestCase):
    """Test cases for prepare_msite_data action plugin."""

    def test_run_basic_functionality(self):
        """Test run with basic functionality."""
        model_data = {
            'vxlan': {
                'multisite': {
                    'overlay': {
                        'vrf_attach_groups': [
                            {
                                'name': 'vrf-group1',
                                'switches': [
                                    {'hostname': 'switch1'},
                                    {'hostname': 'switch2'}
                                ]
                            }
                        ],
                        'network_attach_groups': [
                            {
                                'name': 'net-group1',
                                'switches': [
                                    {'hostname': 'switch1'},
                                    {'hostname': 'switch3'}
                                ]
                            }
                        ],
                        'vrfs': [
                            {'name': 'vrf1', 'vrf_attach_group': 'vrf-group1'},
                            {'name': 'vrf2', 'vrf_attach_group': 'nonexistent-group'}
                        ],
                        'networks': [
                            {'name': 'net1', 'network_attach_group': 'net-group1'},
                            {'name': 'net2', 'network_attach_group': 'nonexistent-group'}
                        ]
                    }
                }
            }
        }
        parent_fabric = "msd-parent"

        mock_msd_response = {
            'response': {
                'DATA': [
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric1', 'fabricType': 'VXLAN_EVPN'},
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric2', 'fabricType': 'VXLAN_EVPN'}
                ]
            }
        }

        mock_fabric_attributes = {'attr1': 'value1'}
        mock_fabric_switches = [
            {'hostname': 'switch1', 'mgmt_ip_address': '10.1.1.1'},
            {'hostname': 'switch2', 'mgmt_ip_address': '10.1.1.2'}
        ]

        task_args = {
            'model_data': model_data,
            'parent_fabric': parent_fabric
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Only mock external dependencies, not the parent run()
        with patch.object(ActionModule, '_execute_module') as mock_execute, \
             patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.prepare_msite_data.ndfc_get_fabric_attributes') as mock_get_attributes, \
             patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.prepare_msite_data.ndfc_get_fabric_switches') as mock_get_switches:

            mock_execute.return_value = mock_msd_response
            mock_get_attributes.return_value = mock_fabric_attributes
            mock_get_switches.return_value = mock_fabric_switches

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertIn('child_fabrics_data', result)
            self.assertIn('overlay_attach_groups', result)

            # Verify child fabrics data structure
            self.assertIn('child-fabric1', result['child_fabrics_data'])
            self.assertIn('child-fabric2', result['child_fabrics_data'])
            self.assertEqual(result['child_fabrics_data']['child-fabric1']['type'], 'VXLAN_EVPN')
            self.assertEqual(result['child_fabrics_data']['child-fabric1']['attributes'], mock_fabric_attributes)
            self.assertEqual(result['child_fabrics_data']['child-fabric1']['switches'], mock_fabric_switches)

    def test_run_switch_hostname_ip_mapping(self):
        """Test run with hostname to IP mapping functionality."""
        model_data = {
            'vxlan': {
                'multisite': {
                    'overlay': {
                        'vrf_attach_groups': [
                            {
                                'name': 'vrf-group1',
                                'switches': [
                                    {'hostname': 'leaf1'},
                                    {'hostname': 'leaf2'}
                                ]
                            }
                        ],
                        'network_attach_groups': [],
                        'vrfs': [{'name': 'vrf1', 'vrf_attach_group': 'vrf-group1'}],
                        'networks': []
                    }
                }
            }
        }
        parent_fabric = "msd-parent"

        mock_msd_response = {
            'response': {
                'DATA': [
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric1', 'fabricType': 'VXLAN_EVPN'}
                ]
            }
        }

        mock_fabric_attributes = {'attr1': 'value1'}
        mock_fabric_switches = [
            {'hostname': 'leaf1', 'mgmt_ip_address': '10.1.1.1'},
            {'hostname': 'leaf2.domain.com', 'mgmt_ip_address': '10.1.1.2'}
        ]

        task_args = {
            'model_data': model_data,
            'parent_fabric': parent_fabric
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(ActionModule, '_execute_module') as mock_execute, \
             patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.prepare_msite_data.ndfc_get_fabric_attributes') as mock_get_attributes, \
             patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.prepare_msite_data.ndfc_get_fabric_switches') as mock_get_switches:

            mock_execute.return_value = mock_msd_response
            mock_get_attributes.return_value = mock_fabric_attributes
            mock_get_switches.return_value = mock_fabric_switches

            result = action_module.run()

            # Check that hostnames are mapped to IP addresses
            vrf_groups = result['overlay_attach_groups']['vrf_attach_groups_dict']
            self.assertIn('vrf-group1', vrf_groups)

            # Find the switch that should have gotten the IP mapping
            leaf1_found = False
            for switch in vrf_groups['vrf-group1']:
                if switch['hostname'] == 'leaf1':
                    self.assertEqual(switch['mgmt_ip_address'], '10.1.1.1')
                    leaf1_found = True
            self.assertTrue(leaf1_found)

    def test_run_empty_model_data(self):
        """Test run with empty model data."""
        model_data = {
            'vxlan': {
                'multisite': {
                    'overlay': {
                        'vrf_attach_groups': [],
                        'network_attach_groups': [],
                        'vrfs': [],
                        'networks': []
                    }
                }
            }
        }
        parent_fabric = "msd-parent"

        mock_msd_response = {
            'response': {
                'DATA': []
            }
        }

        task_args = {
            'model_data': model_data,
            'parent_fabric': parent_fabric
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(ActionModule, '_execute_module') as mock_execute, \
             patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.prepare_msite_data.ndfc_get_fabric_attributes') as mock_get_attributes, \
             patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.prepare_msite_data.ndfc_get_fabric_switches') as mock_get_switches:

            mock_execute.return_value = mock_msd_response
            mock_get_attributes.return_value = {}
            mock_get_switches.return_value = []

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertEqual(result['child_fabrics_data'], {})
            self.assertIn('vrf_attach_groups_dict', result['overlay_attach_groups'])
            self.assertIn('network_attach_groups_dict', result['overlay_attach_groups'])

    def test_run_vrf_attach_group_removal(self):
        """Test run with VRF attach group removal for nonexistent groups."""
        model_data = {
            'vxlan': {
                'multisite': {
                    'overlay': {
                        'vrf_attach_groups': [
                            {
                                'name': 'vrf-group1',
                                'switches': [{'hostname': 'switch1'}]
                            }
                        ],
                        'network_attach_groups': [],
                        'vrfs': [
                            {'name': 'vrf1', 'vrf_attach_group': 'vrf-group1'},
                            {'name': 'vrf2', 'vrf_attach_group': 'nonexistent-group'}
                        ],
                        'networks': []
                    }
                }
            }
        }
        parent_fabric = "msd-parent"

        mock_msd_response = {
            'response': {
                'DATA': [
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric1', 'fabricType': 'VXLAN_EVPN'}
                ]
            }
        }

        task_args = {
            'model_data': model_data,
            'parent_fabric': parent_fabric
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(ActionModule, '_execute_module') as mock_execute, \
             patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.prepare_msite_data.ndfc_get_fabric_attributes') as mock_get_attributes, \
             patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.prepare_msite_data.ndfc_get_fabric_switches') as mock_get_switches:

            mock_execute.return_value = mock_msd_response
            mock_get_attributes.return_value = {}
            mock_get_switches.return_value = []

            result = action_module.run()

            # Check that nonexistent vrf_attach_group is removed
            vrfs = result['overlay_attach_groups']['vrfs']
            vrf1 = next((vrf for vrf in vrfs if vrf['name'] == 'vrf1'), None)
            vrf2 = next((vrf for vrf in vrfs if vrf['name'] == 'vrf2'), None)

            self.assertIsNotNone(vrf1)
            self.assertIn('vrf_attach_group', vrf1)
            self.assertEqual(vrf1['vrf_attach_group'], 'vrf-group1')

            self.assertIsNotNone(vrf2)
            self.assertNotIn('vrf_attach_group', vrf2)  # Should be removed

    def test_run_network_attach_group_removal(self):
        """Test run with network attach group removal for nonexistent groups."""
        model_data = {
            'vxlan': {
                'multisite': {
                    'overlay': {
                        'vrf_attach_groups': [],
                        'network_attach_groups': [
                            {
                                'name': 'net-group1',
                                'switches': [{'hostname': 'switch1'}]
                            }
                        ],
                        'vrfs': [],
                        'networks': [
                            {'name': 'net1', 'network_attach_group': 'net-group1'},
                            {'name': 'net2', 'network_attach_group': 'nonexistent-group'}
                        ]
                    }
                }
            }
        }
        parent_fabric = "msd-parent"

        mock_msd_response = {
            'response': {
                'DATA': [
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric1', 'fabricType': 'VXLAN_EVPN'}
                ]
            }
        }

        task_args = {
            'model_data': model_data,
            'parent_fabric': parent_fabric
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(ActionModule, '_execute_module') as mock_execute, \
             patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.prepare_msite_data.ndfc_get_fabric_attributes') as mock_get_attributes, \
             patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.prepare_msite_data.ndfc_get_fabric_switches') as mock_get_switches:

            mock_execute.return_value = mock_msd_response
            mock_get_attributes.return_value = {}
            mock_get_switches.return_value = []

            result = action_module.run()

            # Check that nonexistent network_attach_group is removed
            networks = result['overlay_attach_groups']['networks']
            net1 = next((net for net in networks if net['name'] == 'net1'), None)
            net2 = next((net for net in networks if net['name'] == 'net2'), None)

            self.assertIsNotNone(net1)
            self.assertIn('network_attach_group', net1)
            self.assertEqual(net1['network_attach_group'], 'net-group1')

            self.assertIsNotNone(net2)
            self.assertNotIn('network_attach_group', net2)  # Should be removed

    def test_run_switches_list_population(self):
        """Test run verifies switches list population."""
        model_data = {
            'vxlan': {
                'multisite': {
                    'overlay': {
                        'vrf_attach_groups': [
                            {
                                'name': 'vrf-group1',
                                'switches': [
                                    {'hostname': 'switch1'},
                                    {'hostname': 'switch2'}
                                ]
                            }
                        ],
                        'network_attach_groups': [
                            {
                                'name': 'net-group1',
                                'switches': [
                                    {'hostname': 'switch3'},
                                    {'hostname': 'switch4'}
                                ]
                            }
                        ],
                        'vrfs': [],
                        'networks': []
                    }
                }
            }
        }
        parent_fabric = "msd-parent"

        mock_msd_response = {
            'response': {
                'DATA': [
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric1', 'fabricType': 'VXLAN_EVPN'}
                ]
            }
        }

        task_args = {
            'model_data': model_data,
            'parent_fabric': parent_fabric
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(ActionModule, '_execute_module') as mock_execute, \
             patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.prepare_msite_data.ndfc_get_fabric_attributes') as mock_get_attributes, \
             patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.prepare_msite_data.ndfc_get_fabric_switches') as mock_get_switches:

            mock_execute.return_value = mock_msd_response
            mock_get_attributes.return_value = {}
            mock_get_switches.return_value = []

            result = action_module.run()

            # Check that switches lists are populated correctly
            overlay = result['overlay_attach_groups']
            self.assertIn('vrf_attach_switches_list', overlay)
            self.assertIn('network_attach_switches_list', overlay)

            # Verify the switches are in the lists
            self.assertIn('switch1', overlay['vrf_attach_switches_list'])
            self.assertIn('switch2', overlay['vrf_attach_switches_list'])
            self.assertIn('switch3', overlay['network_attach_switches_list'])
            self.assertIn('switch4', overlay['network_attach_switches_list'])

    def test_run_regex_hostname_matching(self):
        """Test run with regex hostname matching functionality."""
        model_data = {
            'vxlan': {
                'multisite': {
                    'overlay': {
                        'vrf_attach_groups': [
                            {
                                'name': 'vrf-group1',
                                'switches': [
                                    {'hostname': 'leaf1'},
                                    {'hostname': 'leaf2'}
                                ]
                            }
                        ],
                        'network_attach_groups': [],
                        'vrfs': [],
                        'networks': []
                    }
                }
            }
        }
        parent_fabric = "msd-parent"

        mock_msd_response = {
            'response': {
                'DATA': [
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric1', 'fabricType': 'VXLAN_EVPN'}
                ]
            }
        }

        mock_fabric_attributes = {}
        # Test regex matching - NDFC returns FQDN but data model has just hostname
        mock_fabric_switches = [
            {'hostname': 'leaf1.example.com', 'mgmt_ip_address': '10.1.1.1'},
            {'hostname': 'leaf2.example.com', 'mgmt_ip_address': '10.1.1.2'}
        ]

        task_args = {
            'model_data': model_data,
            'parent_fabric': parent_fabric
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(ActionModule, '_execute_module') as mock_execute, \
             patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.prepare_msite_data.ndfc_get_fabric_attributes') as mock_get_attributes, \
             patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.prepare_msite_data.ndfc_get_fabric_switches') as mock_get_switches:

            mock_execute.return_value = mock_msd_response
            mock_get_attributes.return_value = mock_fabric_attributes
            mock_get_switches.return_value = mock_fabric_switches

            result = action_module.run()

            # Check that regex matching worked for hostname mapping
            vrf_groups = result['overlay_attach_groups']['vrf_attach_groups_dict']
            self.assertIn('vrf-group1', vrf_groups)

            # Both switches should have gotten IP mappings via regex matching
            switches = vrf_groups['vrf-group1']
            for switch in switches:
                self.assertIn('mgmt_ip_address', switch)
                if switch['hostname'] == 'leaf1':
                    self.assertEqual(switch['mgmt_ip_address'], '10.1.1.1')
                elif switch['hostname'] == 'leaf2':
                    self.assertEqual(switch['mgmt_ip_address'], '10.1.1.2')

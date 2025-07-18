"""
Unit tests for manage_child_fabric_vrfs action plugin.
"""
import unittest
from unittest.mock import MagicMock, patch, mock_open
import json

from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.manage_child_fabric_vrfs import ActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.base_test import ActionModuleTestCase


class TestManageChildFabricVrfsActionModule(ActionModuleTestCase):
    """Test cases for manage_child_fabric_vrfs action plugin."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.maxDiff = None

        # Standard mock VRF template config JSON string that matches the test VRF config exactly
        self.standard_vrf_config = '{"ENABLE_NETFLOW": "true", "loopbackId": "100", "vrfTemplate": "Custom_VRF_Template", "advertiseHostRouteFlag": "false", "advertiseDefaultRouteFlag": "false", "configureStaticDefaultRouteFlag": "false", "bgpPassword": "", "bgpPasswordKeyType": "", "NETFLOW_MONITOR": "", "trmEnabled": "false", "loopbackNumber": "", "rpAddress": "", "isRPAbsent": "false", "isRPExternal": "false", "L3VniMcastGroup": "", "multicastGroup": "", "routeTargetImportMvpn": "", "routeTargetExportMvpn": ""}'

        self.mock_msite_data = {
            'overlay_attach_groups': {
                'vrfs': [
                    {
                        'name': 'test_vrf',
                        'vrf_attach_group': 'test_group',
                        'child_fabrics': [
                            {
                                'name': 'child_fabric1',
                                'netflow_enable': True,
                                'loopback_id': 100,
                                'vrf_template': 'Custom_VRF_Template',
                                'adv_host_routes': False,
                                'adv_default_routes': False,
                                'config_static_default_route': False,
                                'bgp_password': '',
                                'bgp_password_key_type': '',
                                'netflow_monitor': '',
                                'trm_enable': False,
                                'rp_loopback_id': '',
                                'rp_address': '',
                                'no_rp': False,
                                'rp_external': False,
                                'underlay_mcast_ip': '',
                                'overlay_multicast_group': '',
                                'import_mvpn_rt': '',
                                'export_mvpn_rt': ''
                            }
                        ]
                    }
                ],
                'vrf_attach_groups': [
                    {
                        'name': 'test_group',
                        'switches': [
                            {'mgmt_ip_address': '10.1.1.1'},
                            {'mgmt_ip_address': '10.1.1.2'}
                        ]
                    }
                ]
            },
            'child_fabrics_data': {
                'child_fabric1': {
                    'type': 'Switch_Fabric',
                    'attributes': {
                        'ENABLE_NETFLOW': 'true'
                    },
                    'switches': [
                        {'mgmt_ip_address': '10.1.1.1'},
                        {'mgmt_ip_address': '10.1.1.3'}
                    ]
                }
            }
        }

    def test_run_no_vrfs(self):
        """Test run with no VRFs to process."""
        msite_data = {
            'overlay_attach_groups': {
                'vrfs': [],
                'vrf_attach_groups': []
            },
            'child_fabrics_data': {}
        }

        task_args = {'msite_data': msite_data}
        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertFalse(result['changed'])
        self.assertFalse(result['failed'])
        self.assertEqual(result['child_fabrics_changed'], [])

    def test_run_no_child_fabrics(self):
        """Test run with VRFs but no child fabrics."""
        msite_data = {
            'overlay_attach_groups': {
                'vrfs': [{'name': 'test_vrf', 'vrf_attach_group': 'test_group'}],
                'vrf_attach_groups': [{'name': 'test_group', 'switches': []}]
            },
            'child_fabrics_data': {}
        }

        task_args = {'msite_data': msite_data}
        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertFalse(result['changed'])
        self.assertEqual(result['child_fabrics_changed'], [])

    def test_run_non_switch_fabric_type(self):
        """Test run with non-Switch_Fabric type child fabrics."""
        task_args = {'msite_data': self.mock_msite_data}
        action_module = self.create_action_module(ActionModule, task_args)

        # Change child fabric type to non-Switch_Fabric
        self.mock_msite_data['child_fabrics_data']['child_fabric1']['type'] = 'External'

        result = action_module.run()

        self.assertFalse(result['changed'])
        self.assertEqual(result['child_fabrics_changed'], [])

    def test_run_netflow_fabric_disabled_error(self):
        """Test run with netflow enabled in VRF but disabled in fabric attributes."""
        msite_data = self.mock_msite_data.copy()
        # Set fabric netflow to false but VRF netflow to true
        msite_data['child_fabrics_data']['child_fabric1']['attributes']['ENABLE_NETFLOW'] = 'false'

        task_args = {'msite_data': msite_data}
        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertTrue(result['failed'])
        self.assertIn('NetFlow is not enabled in the fabric settings', result['msg'])

    def test_run_vrf_no_update_required(self):
        """Test run when VRF configuration matches and no update is needed."""
        task_args = {'msite_data': self.mock_msite_data}
        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC get VRF response with matching config
            mock_execute.return_value = {
                'response': {
                    'DATA': {
                        'fabric': 'child_fabric1',
                        'vrfName': 'test_vrf',
                        'vrfTemplateConfig': self.standard_vrf_config
                    }
                }
            }

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertEqual(result['child_fabrics_changed'], [])

    def test_run_trm_fabric_disabled_error(self):
        """Test run with TRM enabled in VRF but disabled in fabric attributes."""
        msite_data = self.mock_msite_data.copy()
        # Set fabric TRM to false but VRF TRM to true
        msite_data['child_fabrics_data']['child_fabric1']['attributes']['ENABLE_TRM'] = 'false'
        msite_data['overlay_attach_groups']['vrfs'][0]['child_fabrics'][0]['trm_enable'] = True

        task_args = {'msite_data': msite_data}
        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertTrue(result['failed'])
        self.assertIn('TRM is not enabled in the fabric settings', result['msg'])

    def test_run_vrf_update_required(self):
        """Test run when VRF configuration needs to be updated."""
        task_args = {'msite_data': self.mock_msite_data}
        action_module = self.create_action_module(ActionModule, task_args)

        # Mock template file content and path finding
        template_content = '{"vrfName": "{{ dm.name }}", "fabric": "{{ fabric_name }}"}'

        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch.object(action_module, '_find_needle') as mock_find_needle, \
             patch('builtins.open', mock_open(read_data=template_content)):

            # Mock NDFC VRF responses
            mock_execute.side_effect = [
                # First call: get VRF (needs update)
                {
                    'response': {
                        'DATA': {
                            'fabric': 'child_fabric1',
                            'vrfName': 'test_vrf',
                            'vrfTemplateConfig': '{"ENABLE_NETFLOW": "false", "loopbackId": "200", "vrfTemplate": "Different_Template", "advertiseHostRouteFlag": "true", "advertiseDefaultRouteFlag": "true", "configureStaticDefaultRouteFlag": "true", "bgpPassword": "old", "bgpPasswordKeyType": "old", "NETFLOW_MONITOR": "old", "trmEnabled": "true", "loopbackNumber": "old", "rpAddress": "old", "isRPAbsent": "true", "isRPExternal": "true", "L3VniMcastGroup": "old", "multicastGroup": "old", "routeTargetImportMvpn": "old", "routeTargetExportMvpn": "old"}'
                        }
                    }
                },
                # Second call: update VRF (success)
                {
                    'response': {
                        'RETURN_CODE': 200,
                        'MESSAGE': 'OK'
                    }
                }
            ]

            mock_find_needle.return_value = '/path/to/template.j2'

            result = action_module.run(task_vars={'role_path': '/test/role'})

            self.assertTrue(result['changed'])
            self.assertIn('child_fabric1', result['child_fabrics_changed'])
            self.assertEqual(mock_execute.call_count, 2)

    def test_run_template_file_not_found(self):
        """Test run when template file cannot be found."""
        task_args = {'msite_data': self.mock_msite_data}
        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch.object(action_module, '_find_needle') as mock_find_needle:

            # Mock NDFC get VRF response that requires update
            mock_execute.return_value = {
                'response': {
                    'DATA': {
                        'fabric': 'child_fabric1',
                        'vrfName': 'test_vrf',
                        'vrfTemplateConfig': '{"ENABLE_NETFLOW": "false", "loopbackId": "200", "vrfTemplate": "Different_Template", "advertiseHostRouteFlag": "true", "advertiseDefaultRouteFlag": "true", "configureStaticDefaultRouteFlag": "true", "bgpPassword": "old", "bgpPasswordKeyType": "old", "NETFLOW_MONITOR": "old", "trmEnabled": "true", "loopbackNumber": "old", "rpAddress": "old", "isRPAbsent": "true", "isRPExternal": "true", "L3VniMcastGroup": "old", "multicastGroup": "old", "routeTargetImportMvpn": "old", "routeTargetExportMvpn": "old"}'
                    }
                }
            }

            # Mock template file not found
            from ansible.errors import AnsibleFileNotFound
            mock_find_needle.side_effect = AnsibleFileNotFound("Template not found")

            result = action_module.run(task_vars={'role_path': '/test/role'})

            self.assertTrue(result['failed'])
            self.assertIn('Template file not found', result['msg'])

    def test_run_vrf_update_failed(self):
        """Test run when VRF update fails."""
        task_args = {'msite_data': self.mock_msite_data}
        action_module = self.create_action_module(ActionModule, task_args)

        template_content = '{"vrfName": "{{ dm.name }}"}'

        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch.object(action_module, '_find_needle') as mock_find_needle, \
             patch('builtins.open', mock_open(read_data=template_content)):

            # Mock responses
            mock_execute.side_effect = [
                # First call: get VRF (needs update)
                {
                    'response': {
                        'DATA': {
                            'fabric': 'child_fabric1',
                            'vrfName': 'test_vrf',
                            'vrfTemplateConfig': '{"ENABLE_NETFLOW": "false", "loopbackId": "200", "vrfTemplate": "Different_Template", "advertiseHostRouteFlag": "true", "advertiseDefaultRouteFlag": "true", "configureStaticDefaultRouteFlag": "true", "bgpPassword": "old", "bgpPasswordKeyType": "old", "NETFLOW_MONITOR": "old", "trmEnabled": "true", "loopbackNumber": "old", "rpAddress": "old", "isRPAbsent": "true", "isRPExternal": "true", "L3VniMcastGroup": "old", "multicastGroup": "old", "routeTargetImportMvpn": "old", "routeTargetExportMvpn": "old"}'
                        }
                    }
                },
                # Second call: update VRF (fails)
                {
                    'msg': {
                        'RETURN_CODE': 500,
                        'DATA': {
                            'message': 'Internal Server Error'
                        }
                    }
                }
            ]

            mock_find_needle.return_value = '/path/to/template.j2'

            result = action_module.run(task_vars={'role_path': '/test/role'})

            self.assertTrue(result['failed'])
            self.assertIn('Internal Server Error', result['msg'])

    def test_run_vrf_without_child_fabrics_config(self):
        """Test run with VRF that has no child_fabrics configuration."""
        msite_data = {
            'overlay_attach_groups': {
                'vrfs': [
                    {
                        'name': 'test_vrf',
                        'vrf_attach_group': 'test_group'
                        # No child_fabrics key
                    }
                ],
                'vrf_attach_groups': [
                    {
                        'name': 'test_group',
                        'switches': [{'mgmt_ip_address': '10.1.1.1'}]
                    }
                ]
            },
            'child_fabrics_data': {
                'child_fabric1': {
                    'type': 'Switch_Fabric',
                    'attributes': {'ENABLE_NETFLOW': 'true', 'ENABLE_TRM': 'true'},
                    'switches': [{'mgmt_ip_address': '10.1.1.1'}]
                }
            }
        }

        task_args = {'msite_data': msite_data}
        action_module = self.create_action_module(ActionModule, task_args)

        template_content = '{"vrfName": "test_vrf", "fabric": "{{ fabric_name }}"}'

        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch.object(action_module, '_find_needle') as mock_find_needle, \
             patch('builtins.open', mock_open(read_data=template_content)):

            # Mock NDFC responses - VRF needs update due to default values
            mock_execute.side_effect = [
                # First call: get VRF (shows config needs update with default values)
                {
                    'response': {
                        'DATA': {
                            'fabric': 'child_fabric1',
                            'vrfName': 'test_vrf',
                            'vrfTemplateConfig': '{"ENABLE_NETFLOW": "true", "loopbackId": "", "vrfTemplate": "", "advertiseHostRouteFlag": "true", "advertiseDefaultRouteFlag": "true", "configureStaticDefaultRouteFlag": "true", "bgpPassword": "old", "bgpPasswordKeyType": "old", "NETFLOW_MONITOR": "old", "trmEnabled": "true", "loopbackNumber": "old", "rpAddress": "old", "isRPAbsent": "true", "isRPExternal": "true", "L3VniMcastGroup": "old", "multicastGroup": "old", "routeTargetImportMvpn": "old", "routeTargetExportMvpn": "old"}'
                        }
                    }
                },
                # Second call: update VRF (success)
                {
                    'response': {
                        'RETURN_CODE': 200,
                        'MESSAGE': 'OK'
                    }
                }
            ]

            mock_find_needle.return_value = '/path/to/template.j2'

            result = action_module.run(task_vars={'role_path': '/test/role'})

            # Should work with default values for missing child fabric config
            self.assertFalse(result.get('failed', False))
            self.assertTrue(result['changed'])
            self.assertIn('child_fabric1', result['child_fabrics_changed'])

    def test_run_no_switch_intersection(self):
        """Test run with no switch intersection between VRF attach group and child fabric."""
        msite_data = {
            'overlay_attach_groups': {
                'vrfs': [
                    {
                        'name': 'test_vrf',
                        'vrf_attach_group': 'test_group'
                    }
                ],
                'vrf_attach_groups': [
                    {
                        'name': 'test_group',
                        'switches': [
                            {'mgmt_ip_address': '10.1.1.1'},
                            {'mgmt_ip_address': '10.1.1.2'}
                        ]
                    }
                ]
            },
            'child_fabrics_data': {
                'child_fabric1': {
                    'type': 'Switch_Fabric',
                    'attributes': {},
                    'switches': [
                        {'mgmt_ip_address': '10.1.1.5'},  # No intersection
                        {'mgmt_ip_address': '10.1.1.6'}
                    ]
                }
            }
        }

        task_args = {'msite_data': msite_data}
        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertFalse(result['changed'])
        self.assertEqual(result['child_fabrics_changed'], [])


if __name__ == '__main__':
    unittest.main()

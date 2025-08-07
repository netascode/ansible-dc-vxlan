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
Unit tests for manage_child_fabric_networks action plugin.
"""

import unittest
from unittest.mock import patch, mock_open

# Try to import from the plugins directory
try:
    from plugins.action.dtc.manage_child_fabric_networks import ActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.dtc.manage_child_fabric_networks import ActionModule
from .base_test import ActionModuleTestCase


class TestManageChildFabricNetworksActionModule(ActionModuleTestCase):
    """Test cases for manage_child_fabric_networks action plugin."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.maxDiff = None
        self.mock_nd_version = '3.2.2m'
        self.mock_msite_data = {
            'overlay_attach_groups': {
                'networks': [
                    {
                        'name': 'test_network',
                        'network_attach_group': 'test_group',
                        'child_fabrics': [
                            {
                                'name': 'child_fabric1',
                                'netflow_enable': True,
                                'trm_enable': True,
                                'dhcp_loopback_id': '100',
                                'vlan_netflow_monitor': 'test_monitor',
                                'multicast_group_address': '239.1.1.1'
                            }
                        ]
                    }
                ],
                'network_attach_groups': [
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
                        'ENABLE_NETFLOW': 'true',
                        'ENABLE_TRM': 'true'
                    },
                    'switches': [
                        {'mgmt_ip_address': '10.1.1.1'},
                        {'mgmt_ip_address': '10.1.1.3'}
                    ]
                },
                'child_fabric2': {
                    'type': 'External',
                    'attributes': {},
                    'switches': []
                }
            }
        }

    def test_run_no_networks(self):
        """Test run with no networks to process."""
        msite_data = {
            'overlay_attach_groups': {
                'networks': [],
                'network_attach_groups': []
            },
            'child_fabrics_data': {}
        }

        task_args = {
            'nd_version': self.mock_nd_version,
            'msite_data': msite_data
        }
        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertFalse(result['changed'])
        self.assertFalse(result['failed'])
        self.assertEqual(result['child_fabrics_changed'], [])

    def test_run_no_child_fabrics(self):
        """Test run with networks but no child fabrics."""
        msite_data = {
            'overlay_attach_groups': {
                'networks': [{'name': 'test_net', 'network_attach_group': 'test_group'}],
                'network_attach_groups': [{'name': 'test_group', 'switches': []}]
            },
            'child_fabrics_data': {}
        }

        task_args = {
            'nd_version': self.mock_nd_version,
            'msite_data': msite_data
        }
        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertFalse(result['changed'])
        self.assertEqual(result['child_fabrics_changed'], [])

    def test_run_non_switch_fabric_type(self):
        """Test run with non-Switch_Fabric type child fabrics."""
        task_args = {
            'nd_version': self.mock_nd_version,
            'msite_data': self.mock_msite_data
        }
        action_module = self.create_action_module(ActionModule, task_args)

        # Change child fabric type to non-Switch_Fabric
        self.mock_msite_data['child_fabrics_data']['child_fabric1']['type'] = 'External'

        result = action_module.run()

        self.assertFalse(result['changed'])
        self.assertEqual(result['child_fabrics_changed'], [])

    def test_run_no_switch_intersection(self):
        """Test run with no switch intersection between network attach group and child fabric."""
        msite_data = {
            'overlay_attach_groups': {
                'networks': [
                    {
                        'name': 'test_network',
                        'network_attach_group': 'test_group'
                    }
                ],
                'network_attach_groups': [
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

        task_args = {
            'nd_version': self.mock_nd_version,
            'msite_data': msite_data
        }
        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertFalse(result['changed'])
        self.assertEqual(result['child_fabrics_changed'], [])

    def test_run_netflow_fabric_disabled_error(self):
        """Test run with netflow enabled in network but disabled in fabric attributes."""
        msite_data = self.mock_msite_data.copy()
        # Set fabric netflow to false but network netflow to true
        msite_data['child_fabrics_data']['child_fabric1']['attributes']['ENABLE_NETFLOW'] = 'false'

        task_args = {
            'nd_version': self.mock_nd_version,
            'msite_data': msite_data
        }
        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertTrue(result['failed'])
        self.assertIn('NetFlow is not enabled in the fabric settings', result['msg'])

    def test_run_trm_fabric_disabled_error(self):
        """Test run with TRM enabled in network but disabled in fabric attributes."""
        msite_data = self.mock_msite_data.copy()
        # Set fabric TRM to false but network TRM to true
        msite_data['child_fabrics_data']['child_fabric1']['attributes']['ENABLE_TRM'] = 'false'

        task_args = {
            'nd_version': self.mock_nd_version,
            'msite_data': msite_data
        }
        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertTrue(result['failed'])
        self.assertIn('TRM is not enabled in the fabric settings', result['msg'])

    def test_run_network_update_required(self):
        """Test run when network configuration needs to be updated."""
        task_args = {
            'nd_version': self.mock_nd_version,
            'msite_data': self.mock_msite_data
        }
        action_module = self.create_action_module(ActionModule, task_args)

        # Mock template file content and path finding
        template_content = '{"networkName": "{{ network_name }}", "fabric": "{{ fabric_name }}"}'

        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch.object(action_module, '_find_needle') as mock_find_needle, \
             patch('builtins.open', mock_open(read_data=template_content)):

            # Mock NDFC get network response
            mock_execute.side_effect = [
                # First call: get network
                {
                    'response': {
                        'DATA': {
                            'fabric': 'child_fabric1',
                            'networkName': 'test_network',
                            'networkTemplateConfig': (
                                '{"ENABLE_NETFLOW": "false", '
                                '"VLAN_NETFLOW_MONITOR": "", '
                                '"trmEnabled": "false", '
                                '"mcastGroup": "239.1.1.2", '
                                '"loopbackId": ""}'
                            )
                        }
                    }
                },
                # Second call: update network
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

    def test_run_network_no_update_required(self):
        """Test run when network configuration matches and no update is needed."""
        task_args = {
            'nd_version': self.mock_nd_version,
            'msite_data': self.mock_msite_data
        }
        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(action_module, '_execute_module') as mock_execute:
            # Mock NDFC get network response with matching config
            mock_execute.return_value = {
                'response': {
                    'DATA': {
                        'fabric': 'child_fabric1',
                        'networkName': 'test_network',
                        'networkTemplateConfig': (
                            '{"ENABLE_NETFLOW": "true", '
                            '"VLAN_NETFLOW_MONITOR": "test_monitor", '
                            '"trmEnabled": "true", '
                            '"mcastGroup": "239.1.1.1", '
                            '"loopbackId": "100"}'
                        )
                    }
                }
            }

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertEqual(result['child_fabrics_changed'], [])

    def test_run_template_file_not_found(self):
        """Test run when template file cannot be found."""
        task_args = {
            'nd_version': self.mock_nd_version,
            'msite_data': self.mock_msite_data
        }
        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch.object(action_module, '_find_needle') as mock_find_needle:

            # Mock NDFC get network response that requires update
            mock_execute.return_value = {
                'response': {
                    'DATA': {
                        'fabric': 'child_fabric1',
                        'networkName': 'test_network',
                        'networkTemplateConfig': (
                            '{"ENABLE_NETFLOW": "false", '
                            '"VLAN_NETFLOW_MONITOR": "", '
                            '"trmEnabled": "false", '
                            '"mcastGroup": "239.1.1.2", '
                            '"loopbackId": ""}'
                        )
                    }
                }
            }

            # Mock template file not found
            from ansible.errors import AnsibleFileNotFound
            mock_find_needle.side_effect = AnsibleFileNotFound("Template not found")

            result = action_module.run(task_vars={'role_path': '/test/role'})

            self.assertTrue(result['failed'])
            self.assertIn('Template file not found', result['msg'])

    def test_run_network_update_failed(self):
        """Test run when network update fails."""
        task_args = {
            'nd_version': self.mock_nd_version,
            'msite_data': self.mock_msite_data
        }
        action_module = self.create_action_module(ActionModule, task_args)

        template_content = '{"networkName": "{{ network_name }}"}'

        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch.object(action_module, '_find_needle') as mock_find_needle, \
             patch('builtins.open', mock_open(read_data=template_content)):

            # Mock responses
            mock_execute.side_effect = [
                # First call: get network (needs update)
                {
                    'response': {
                        'DATA': {
                            'fabric': 'child_fabric1',
                            'networkName': 'test_network',
                            'networkTemplateConfig': (
                                '{"ENABLE_NETFLOW": "false", '
                                '"VLAN_NETFLOW_MONITOR": "", '
                                '"trmEnabled": "false", '
                                '"mcastGroup": "239.1.1.2", '
                                '"loopbackId": ""}'
                            )
                        }
                    }
                },
                # Second call: update network (fails)
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

    def test_run_network_without_child_fabrics_config(self):
        """Test run with network that has no child_fabrics configuration."""
        msite_data = {
            'overlay_attach_groups': {
                'networks': [
                    {
                        'name': 'test_network',
                        'network_attach_group': 'test_group'
                        # No child_fabrics key
                    }
                ],
                'network_attach_groups': [
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

        task_args = {
            'nd_version': self.mock_nd_version,
            'msite_data': msite_data
        }
        action_module = self.create_action_module(ActionModule, task_args)

        template_content = '{"networkName": "{{ network_name }}", "fabric": "{{ fabric_name }}"}'

        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch.object(action_module, '_find_needle') as mock_find_needle, \
             patch('builtins.open', mock_open(read_data=template_content)):

            # Mock NDFC responses - need two calls: GET then PUT
            mock_execute.side_effect = [
                # First call: get network (shows config needs update)
                {
                    'response': {
                        'DATA': {
                            'fabric': 'child_fabric1',
                            'networkName': 'test_network',
                            'networkTemplateConfig': (
                                '{"ENABLE_NETFLOW": "true", '
                                '"VLAN_NETFLOW_MONITOR": "", '
                                '"trmEnabled": "false", '
                                '"mcastGroup": "", '
                                '"loopbackId": ""}'
                            )
                        }
                    }
                },
                # Second call: update network (success)
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


if __name__ == '__main__':
    unittest.main()

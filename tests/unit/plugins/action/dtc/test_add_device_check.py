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
Unit tests for add_device_check action plugin.
"""

import unittest
from unittest.mock import patch

# Try to import from the plugins directory
try:
    from plugins.action.dtc.add_device_check import ActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.dtc.add_device_check import ActionModule

from .base_test import ActionModuleTestCase


class TestAddDeviceCheckActionModule(ActionModuleTestCase):
    """Test cases for add_device_check action plugin."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.action_module = self.create_action_module(ActionModule)

    def test_run_valid_fabric_data(self):
        """Test run with valid fabric data."""
        fabric_data = {
            'global': {
                'auth_proto': 'md5'
            },
            'topology': {
                'switches': [
                    {
                        'name': 'switch1',
                        'management': {'ip': '192.168.1.1'},
                        'role': 'spine'
                    },
                    {
                        'name': 'switch2',
                        'management': {'ip': '192.168.1.2'},
                        'role': 'leaf'
                    }
                ]
            }
        }

        task_args = {
            'fabric_data': fabric_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)

    def test_run_missing_auth_proto(self):
        """Test run when auth_proto is missing."""
        fabric_data = {
            'global': {},
            'topology': {
                'switches': [
                    {
                        'name': 'switch1',
                        'management': {'ip': '192.168.1.1'},
                        'role': 'spine'
                    }
                ]
            }
        }

        task_args = {
            'fabric_data': fabric_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertTrue(result['failed'])
            self.assertIn("Data model path 'vxlan.global.auth_proto' must be defined!", result['msg'])

    def test_run_missing_global_section(self):
        """Test run when global section is missing."""
        fabric_data = {
            'topology': {
                'switches': [
                    {
                        'name': 'switch1',
                        'management': {'ip': '192.168.1.1'},
                        'role': 'spine'
                    }
                ]
            }
        }

        task_args = {
            'fabric_data': fabric_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            # The plugin doesn't handle None from fabric_data.get('global')
            # It will throw AttributeError when trying to call get() on None
            with self.assertRaises(AttributeError):
                action_module.run()

    def test_run_missing_management_in_switch(self):
        """Test run when management is missing in switch."""
        fabric_data = {
            'global': {
                'auth_proto': 'md5'
            },
            'topology': {
                'switches': [
                    {
                        'name': 'switch1',
                        'role': 'spine'
                        # Missing management
                    }
                ]
            }
        }

        task_args = {
            'fabric_data': fabric_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertTrue(result['failed'])
            self.assertIn("Data model path 'vxlan.topology.switches.switch1.management' must be defined!", result['msg'])

    def test_run_missing_role_in_switch(self):
        """Test run when role is missing in switch."""
        fabric_data = {
            'global': {
                'auth_proto': 'md5'
            },
            'topology': {
                'switches': [
                    {
                        'name': 'switch1',
                        'management': {'ip': '192.168.1.1'}
                        # Missing role
                    }
                ]
            }
        }

        task_args = {
            'fabric_data': fabric_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertTrue(result['failed'])
            self.assertIn("Data model path 'vxlan.topology.switches.switch1.role' must be defined!", result['msg'])

    def test_run_no_switches(self):
        """Test run when no switches are defined."""
        fabric_data = {
            'global': {
                'auth_proto': 'md5'
            },
            'topology': {
                'switches': None
            }
        }

        task_args = {
            'fabric_data': fabric_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)

    def test_run_empty_switches_list(self):
        """Test run when switches list is empty."""
        fabric_data = {
            'global': {
                'auth_proto': 'md5'
            },
            'topology': {
                'switches': []
            }
        }

        task_args = {
            'fabric_data': fabric_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)

    def test_run_missing_topology_section(self):
        """Test run when topology section is missing."""
        fabric_data = {
            'global': {
                'auth_proto': 'md5'
            }
        }

        task_args = {
            'fabric_data': fabric_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            # The plugin doesn't handle None from fabric_data.get('topology')
            # It will throw AttributeError when trying to call get() on None
            with self.assertRaises(AttributeError):
                action_module.run()

    def test_run_multiple_switches_with_errors(self):
        """Test run with multiple switches where some have errors."""
        fabric_data = {
            'global': {
                'auth_proto': 'md5'
            },
            'topology': {
                'switches': [
                    {
                        'name': 'switch1',
                        'management': {'ip': '192.168.1.1'},
                        'role': 'spine'
                    },
                    {
                        'name': 'switch2',
                        'management': {'ip': '192.168.1.2'}
                        # Missing role
                    },
                    {
                        'name': 'switch3',
                        'role': 'leaf'
                        # Missing management
                    }
                ]
            }
        }

        task_args = {
            'fabric_data': fabric_data
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertTrue(result['failed'])
            # Should fail on the first error encountered (switch2 missing role)
            self.assertIn("Data model path 'vxlan.topology.switches.switch2.role' must be defined!", result['msg'])

    def test_run_switches_with_different_auth_proto_values(self):
        """Test run with different auth_proto values."""
        auth_proto_values = ['md5', 'sha1', 'cleartext', None]

        for auth_proto in auth_proto_values:
            with self.subTest(auth_proto=auth_proto):
                fabric_data = {
                    'global': {
                        'auth_proto': auth_proto
                    },
                    'topology': {
                        'switches': [
                            {
                                'name': 'switch1',
                                'management': {'ip': '192.168.1.1'},
                                'role': 'spine'
                            }
                        ]
                    }
                }

                task_args = {
                    'fabric_data': fabric_data
                }

                action_module = self.create_action_module(ActionModule, task_args)

                # Mock the run method from parent class
                with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
                    mock_parent_run.return_value = {'changed': False}

                    result = action_module.run()

                    if auth_proto is None:
                        self.assertTrue(result['failed'])
                        self.assertIn("Data model path 'vxlan.global.auth_proto' must be defined!", result['msg'])
                    else:
                        self.assertFalse(result['failed'])


if __name__ == '__main__':
    unittest.main()

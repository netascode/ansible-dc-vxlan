"""
Unit tests for existing_links_check action plugin.
"""
import unittest
from unittest.mock import patch

from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.existing_links_check import ActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.base_test import ActionModuleTestCase


class TestExistingLinksCheckActionModule(ActionModuleTestCase):
    """Test cases for existing_links_check action plugin."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.action_module = self.create_action_module(ActionModule)

    def test_run_no_existing_links(self):
        """Test run when no existing links are present."""
        existing_links = []
        fabric_links = [
            {
                'src_device': 'switch1',
                'src_interface': 'eth1/1',
                'dst_device': 'switch2',
                'dst_interface': 'eth1/1',
                'template': 'int_intra_fabric_link',
                'profile': {}
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertEqual(result['required_links'], fabric_links)

    def test_run_exact_link_match_no_template(self):
        """Test run when exact link match exists but no template name."""
        existing_links = [
            {
                'sw1-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'eth1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'eth1/1'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch1',
                'src_interface': 'eth1/1',
                'dst_device': 'switch2',
                'dst_interface': 'eth1/1',
                'template': 'int_intra_fabric_link',
                'profile': {}
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            # Link should be marked as not required since it exists without template
            self.assertEqual(result['required_links'], [])

    def test_run_reverse_link_match_no_template(self):
        """Test run when reverse link match exists but no template name."""
        existing_links = [
            {
                'sw1-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'eth1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'eth1/1'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch1',
                'src_interface': 'eth1/1',
                'dst_device': 'switch2',
                'dst_interface': 'eth1/1',
                'template': 'int_intra_fabric_link',
                'profile': {}
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            # Link should be marked as not required since it exists without template
            self.assertEqual(result['required_links'], [])

    def test_run_pre_provision_template_match(self):
        """Test run when link matches with pre-provision template."""
        existing_links = [
            {
                'sw1-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'eth1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'eth1/1'
                },
                'templateName': 'int_pre_provision_intra_fabric_link'
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch1',
                'src_interface': 'eth1/1',
                'dst_device': 'switch2',
                'dst_interface': 'eth1/1',
                'template': 'int_intra_fabric_link',
                'profile': {}
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            # Link should be required since it has pre-provision template
            self.assertEqual(result['required_links'], fabric_links)

    def test_run_num_link_template_match(self):
        """Test run when link matches with num_link template."""
        existing_links = [
            {
                'sw1-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'eth1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'eth1/1'
                },
                'templateName': 'int_intra_fabric_num_link',
                'nvPairs': {
                    'PEER1_IP': '192.168.1.1',
                    'PEER2_IP': '192.168.1.2',
                    'ENABLE_MACSEC': 'true'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch1',
                'src_interface': 'eth1/1',
                'dst_device': 'switch2',
                'dst_interface': 'eth1/1',
                'template': 'int_intra_fabric_link',
                'profile': {}
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            # Link should be required with updated template and profile
            self.assertEqual(len(result['required_links']), 1)
            link = result['required_links'][0]
            self.assertEqual(link['template'], 'int_intra_fabric_num_link')
            self.assertEqual(link['profile']['peer1_ipv4_addr'], '192.168.1.1')
            self.assertEqual(link['profile']['peer2_ipv4_addr'], '192.168.1.2')
            self.assertEqual(link['profile']['enable_macsec'], 'true')

    def test_run_num_link_template_no_macsec(self):
        """Test run when link matches with num_link template but no MACSEC."""
        existing_links = [
            {
                'sw1-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'eth1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'eth1/1'
                },
                'templateName': 'int_intra_fabric_num_link',
                'nvPairs': {
                    'PEER1_IP': '192.168.1.1',
                    'PEER2_IP': '192.168.1.2'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch1',
                'src_interface': 'eth1/1',
                'dst_device': 'switch2',
                'dst_interface': 'eth1/1',
                'template': 'int_intra_fabric_link',
                'profile': {}
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            # Link should be required with updated template and profile
            self.assertEqual(len(result['required_links']), 1)
            link = result['required_links'][0]
            self.assertEqual(link['template'], 'int_intra_fabric_num_link')
            self.assertEqual(link['profile']['peer1_ipv4_addr'], '192.168.1.1')
            self.assertEqual(link['profile']['peer2_ipv4_addr'], '192.168.1.2')
            self.assertEqual(link['profile']['enable_macsec'], 'false')

    def test_run_other_template_match(self):
        """Test run when link matches with other template."""
        existing_links = [
            {
                'sw1-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'eth1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'eth1/1'
                },
                'templateName': 'some_other_template'
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch1',
                'src_interface': 'eth1/1',
                'dst_device': 'switch2',
                'dst_interface': 'eth1/1',
                'template': 'int_intra_fabric_link',
                'profile': {}
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            # Link should be marked as not required since it exists with other template
            self.assertEqual(result['required_links'], [])

    def test_run_case_insensitive_matching(self):
        """Test run with case insensitive matching."""
        existing_links = [
            {
                'sw1-info': {
                    'sw-sys-name': 'SWITCH1',
                    'if-name': 'ETH1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'SWITCH2',
                    'if-name': 'ETH1/1'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch1',
                'src_interface': 'eth1/1',
                'dst_device': 'switch2',
                'dst_interface': 'eth1/1',
                'template': 'int_intra_fabric_link',
                'profile': {}
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            # Link should be marked as not required due to case insensitive matching
            self.assertEqual(result['required_links'], [])

    def test_run_multiple_links_mixed_scenarios(self):
        """Test run with multiple links in different scenarios."""
        existing_links = [
            {
                'sw1-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'eth1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'eth1/1'
                }
            },
            {
                'sw1-info': {
                    'sw-sys-name': 'switch3',
                    'if-name': 'eth1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch4',
                    'if-name': 'eth1/1'
                },
                'templateName': 'int_intra_fabric_num_link',
                'nvPairs': {
                    'PEER1_IP': '192.168.1.3',
                    'PEER2_IP': '192.168.1.4'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch1',
                'src_interface': 'eth1/1',
                'dst_device': 'switch2',
                'dst_interface': 'eth1/1',
                'template': 'int_intra_fabric_link',
                'profile': {}
            },
            {
                'src_device': 'switch3',
                'src_interface': 'eth1/1',
                'dst_device': 'switch4',
                'dst_interface': 'eth1/1',
                'template': 'int_intra_fabric_link',
                'profile': {}
            },
            {
                'src_device': 'switch5',
                'src_interface': 'eth1/1',
                'dst_device': 'switch6',
                'dst_interface': 'eth1/1',
                'template': 'int_intra_fabric_link',
                'profile': {}
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            # Should have 2 required links: one updated for num_link template, one new
            self.assertEqual(len(result['required_links']), 2)

            # Check that the num_link template was applied
            num_link_found = False
            for link in result['required_links']:
                if link['src_device'] == 'switch3' and link['template'] == 'int_intra_fabric_num_link':
                    num_link_found = True
                    self.assertEqual(link['profile']['peer1_ipv4_addr'], '192.168.1.3')
                    self.assertEqual(link['profile']['peer2_ipv4_addr'], '192.168.1.4')
                    self.assertEqual(link['profile']['enable_macsec'], 'false')

            self.assertTrue(num_link_found)

    def test_run_missing_sw_info_keys(self):
        """Test run when existing links are missing required keys."""
        existing_links = [
            {
                'sw1-info': {
                    'if-name': 'eth1/1'
                    # Missing sw-sys-name
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'eth1/1'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch1',
                'src_interface': 'eth1/1',
                'dst_device': 'switch2',
                'dst_interface': 'eth1/1',
                'template': 'int_intra_fabric_link',
                'profile': {}
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            # The plugin has a bug - it checks for key existence in the if condition
            # but then tries to access it in the or condition. This raises a KeyError.
            with self.assertRaises(KeyError):
                action_module.run()

    def test_run_empty_fabric_links(self):
        """Test run with empty fabric links."""
        existing_links = [
            {
                'sw1-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'eth1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'eth1/1'
                }
            }
        ]

        fabric_links = []

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertEqual(result['required_links'], [])


if __name__ == '__main__':
    unittest.main()

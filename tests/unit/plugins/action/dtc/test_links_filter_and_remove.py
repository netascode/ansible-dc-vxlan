"""
Unit tests for links_filter_and_remove action plugin.
"""
from unittest.mock import patch

from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.links_filter_and_remove import ActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.base_test import ActionModuleTestCase


class TestLinksFilterAndRemoveActionModule(ActionModuleTestCase):
    """Test cases for links_filter_and_remove action plugin."""

    def test_run_exact_link_match_to_remove(self):
        """Test run with exact link match that should be removed."""
        existing_links = [
            {
                'templateName': 'int_intra_fabric_num_link',
                'fabricName': 'test-fabric',
                'sw1-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'Ethernet1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'Ethernet1/2'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch3',
                'src_interface': 'Ethernet1/3',
                'dst_device': 'switch4',
                'dst_interface': 'Ethernet1/4'
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertEqual(len(result['links_to_be_removed']), 1)
        self.assertEqual(result['links_to_be_removed'][0]['dst_fabric'], 'test-fabric')

    def test_run_exact_link_match_keep_link(self):
        """Test run with exact link match that should be kept."""
        existing_links = [
            {
                'templateName': 'int_intra_fabric_num_link',
                'fabricName': 'test-fabric',
                'sw1-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'Ethernet1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'Ethernet1/2'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch1',
                'src_interface': 'Ethernet1/1',
                'dst_device': 'switch2',
                'dst_interface': 'Ethernet1/2'
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertEqual(len(result['links_to_be_removed']), 0)

    def test_run_reverse_link_match_keep_link(self):
        """Test run with reverse link match that should be kept."""
        existing_links = [
            {
                'templateName': 'int_intra_fabric_num_link',
                'fabricName': 'test-fabric',
                'sw1-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'Ethernet1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'Ethernet1/2'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch2',
                'src_interface': 'Ethernet1/2',
                'dst_device': 'switch1',
                'dst_interface': 'Ethernet1/1'
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertEqual(len(result['links_to_be_removed']), 0)

    def test_run_case_insensitive_matching(self):
        """Test run verifies case insensitive matching."""
        existing_links = [
            {
                'templateName': 'int_intra_fabric_num_link',
                'fabricName': 'test-fabric',
                'sw1-info': {
                    'sw-sys-name': 'SWITCH1',
                    'if-name': 'ETHERNET1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'SWITCH2',
                    'if-name': 'ETHERNET1/2'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch1',
                'src_interface': 'ethernet1/1',
                'dst_device': 'switch2',
                'dst_interface': 'ethernet1/2'
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertEqual(len(result['links_to_be_removed']), 0)

    def test_run_pre_provision_template_match(self):
        """Test run with pre-provision template that should be considered."""
        existing_links = [
            {
                'templateName': 'int_pre_provision_intra_fabric_link',
                'fabricName': 'test-fabric',
                'sw1-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'Ethernet1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'Ethernet1/2'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch3',
                'src_interface': 'Ethernet1/3',
                'dst_device': 'switch4',
                'dst_interface': 'Ethernet1/4'
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertEqual(len(result['links_to_be_removed']), 1)

    def test_run_other_template_ignored(self):
        """Test run with other template types that should be ignored."""
        existing_links = [
            {
                'templateName': 'other_template',
                'fabricName': 'test-fabric',
                'sw1-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'Ethernet1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'Ethernet1/2'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch3',
                'src_interface': 'Ethernet1/3',
                'dst_device': 'switch4',
                'dst_interface': 'Ethernet1/4'
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertEqual(len(result['links_to_be_removed']), 0)

    def test_run_missing_template_name(self):
        """Test run with missing template name should be ignored."""
        existing_links = [
            {
                'fabricName': 'test-fabric',
                'sw1-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'Ethernet1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'Ethernet1/2'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch3',
                'src_interface': 'Ethernet1/3',
                'dst_device': 'switch4',
                'dst_interface': 'Ethernet1/4'
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertEqual(len(result['links_to_be_removed']), 0)

    def test_run_missing_fabric_name_skip_removal(self):
        """Test run with missing fabric name should skip removal."""
        existing_links = [
            {
                'templateName': 'int_intra_fabric_num_link',
                'sw1-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'Ethernet1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'Ethernet1/2'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch3',
                'src_interface': 'Ethernet1/3',
                'dst_device': 'switch4',
                'dst_interface': 'Ethernet1/4'
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertEqual(len(result['links_to_be_removed']), 0)

    def test_run_missing_sw_info_keys(self):
        """Test run with missing sw-info keys should raise KeyError."""
        existing_links = [
            {
                'templateName': 'int_intra_fabric_num_link',
                'fabricName': 'test-fabric',
                'sw1-info': {
                    'sw-sys-name': 'switch1'
                    # Missing 'if-name'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'Ethernet1/2'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch1',
                'src_interface': 'Ethernet1/1',
                'dst_device': 'switch2',
                'dst_interface': 'Ethernet1/2'
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Should raise KeyError due to missing 'if-name' key
        with self.assertRaises(KeyError):
            action_module.run()

    def test_run_empty_existing_links(self):
        """Test run with empty existing links list."""
        existing_links = []

        fabric_links = [
            {
                'src_device': 'switch1',
                'src_interface': 'Ethernet1/1',
                'dst_device': 'switch2',
                'dst_interface': 'Ethernet1/2'
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertEqual(len(result['links_to_be_removed']), 0)

    def test_run_empty_fabric_links(self):
        """Test run with empty fabric links list."""
        existing_links = [
            {
                'templateName': 'int_intra_fabric_num_link',
                'fabricName': 'test-fabric',
                'sw1-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'Ethernet1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'Ethernet1/2'
                }
            }
        ]

        fabric_links = []

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertEqual(len(result['links_to_be_removed']), 1)

    def test_run_multiple_links_mixed_scenarios(self):
        """Test run with multiple links and mixed scenarios."""
        existing_links = [
            {
                'templateName': 'int_intra_fabric_num_link',
                'fabricName': 'test-fabric',
                'sw1-info': {
                    'sw-sys-name': 'switch1',
                    'if-name': 'Ethernet1/1'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch2',
                    'if-name': 'Ethernet1/2'
                }
            },
            {
                'templateName': 'int_intra_fabric_num_link',
                'fabricName': 'test-fabric',
                'sw1-info': {
                    'sw-sys-name': 'switch3',
                    'if-name': 'Ethernet1/3'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch4',
                    'if-name': 'Ethernet1/4'
                }
            },
            {
                'templateName': 'int_intra_fabric_num_link',
                'fabricName': 'test-fabric',
                'sw1-info': {
                    'sw-sys-name': 'switch5',
                    'if-name': 'Ethernet1/5'
                },
                'sw2-info': {
                    'sw-sys-name': 'switch6',
                    'if-name': 'Ethernet1/6'
                }
            }
        ]

        fabric_links = [
            {
                'src_device': 'switch1',
                'src_interface': 'Ethernet1/1',
                'dst_device': 'switch2',
                'dst_interface': 'Ethernet1/2'
            }
        ]

        task_args = {
            'existing_links': existing_links,
            'fabric_links': fabric_links
        }

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        # Should remove 2 links (switch3-4 and switch5-6), keep 1 (switch1-2)
        self.assertEqual(len(result['links_to_be_removed']), 2)

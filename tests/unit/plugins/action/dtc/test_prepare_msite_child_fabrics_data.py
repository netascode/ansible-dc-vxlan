"""
Unit tests for prepare_msite_child_fabrics_data action plugin.
"""
from unittest.mock import patch

from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.prepare_msite_child_fabrics_data import ActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.base_test import ActionModuleTestCase


class TestPrepareMsiteChildFabricsDataActionModule(ActionModuleTestCase):
    """Test cases for prepare_msite_child_fabrics_data action plugin."""

    def test_run_add_new_child_fabrics(self):
        """Test run when new child fabrics need to be added."""
        parent_fabric = "msd-parent"
        child_fabrics = [
            {'name': 'child-fabric1'},
            {'name': 'child-fabric2'},
            {'name': 'child-fabric3'}
        ]

        # Currently no child fabrics are associated
        mock_msd_response = {
            'response': {
                'DATA': []
            }
        }

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Only mock _execute_module, not the parent run()
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_msd_response

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertEqual(result['current_associated_child_fabrics'], [])
            self.assertEqual(result['to_be_removed'], [])
            self.assertEqual(set(result['to_be_added']), {'child-fabric1', 'child-fabric2', 'child-fabric3'})

    def test_run_remove_existing_child_fabrics(self):
        """Test run when existing child fabrics need to be removed."""
        parent_fabric = "msd-parent"
        child_fabrics = [
            {'name': 'child-fabric1'}  # Only keeping one fabric
        ]

        # Currently has three child fabrics associated
        mock_msd_response = {
            'response': {
                'DATA': [
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric1'},
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric2'},
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric3'},
                    {'fabricParent': 'other-parent', 'fabricName': 'other-child'}  # Different parent
                ]
            }
        }

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_msd_response

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertEqual(set(result['current_associated_child_fabrics']), {'child-fabric1', 'child-fabric2', 'child-fabric3'})
            self.assertEqual(set(result['to_be_removed']), {'child-fabric2', 'child-fabric3'})
            self.assertEqual(result['to_be_added'], [])

    def test_run_mixed_add_remove_scenarios(self):
        """Test run with mixed add and remove scenarios."""
        parent_fabric = "msd-parent"
        child_fabrics = [
            {'name': 'child-fabric1'},  # Keep existing
            {'name': 'child-fabric3'},  # Add new
            {'name': 'child-fabric4'}   # Add new
        ]

        # Currently has child-fabric1 and child-fabric2
        mock_msd_response = {
            'response': {
                'DATA': [
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric1'},
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric2'},
                    {'fabricParent': 'other-parent', 'fabricName': 'other-child'}
                ]
            }
        }

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_msd_response

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertEqual(set(result['current_associated_child_fabrics']), {'child-fabric1', 'child-fabric2'})
            self.assertEqual(result['to_be_removed'], ['child-fabric2'])  # Remove child-fabric2
            self.assertEqual(set(result['to_be_added']), {'child-fabric3', 'child-fabric4'})  # Add new ones

    def test_run_no_changes_needed(self):
        """Test run when no changes are needed."""
        parent_fabric = "msd-parent"
        child_fabrics = [
            {'name': 'child-fabric1'},
            {'name': 'child-fabric2'}
        ]

        # Currently has exactly the same child fabrics
        mock_msd_response = {
            'response': {
                'DATA': [
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric1'},
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric2'},
                    {'fabricParent': 'other-parent', 'fabricName': 'other-child'}
                ]
            }
        }

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_msd_response

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertEqual(set(result['current_associated_child_fabrics']), {'child-fabric1', 'child-fabric2'})
            self.assertEqual(result['to_be_removed'], [])
            self.assertEqual(result['to_be_added'], [])

    def test_run_empty_child_fabrics_list(self):
        """Test run with empty child fabrics list (remove all)."""
        parent_fabric = "msd-parent"
        child_fabrics = []

        mock_msd_response = {
            'response': {
                'DATA': [
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric1'},
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric2'}
                ]
            }
        }

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_msd_response

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertEqual(set(result['current_associated_child_fabrics']), {'child-fabric1', 'child-fabric2'})
            self.assertEqual(set(result['to_be_removed']), {'child-fabric1', 'child-fabric2'})
            self.assertEqual(result['to_be_added'], [])

    def test_run_empty_msd_response(self):
        """Test run with empty MSD fabric associations response."""
        parent_fabric = "msd-parent"
        child_fabrics = [
            {'name': 'child-fabric1'}
        ]

        mock_msd_response = {
            'response': {
                'DATA': []
            }
        }

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_msd_response

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertEqual(result['current_associated_child_fabrics'], [])
            self.assertEqual(result['to_be_removed'], [])
            self.assertEqual(result['to_be_added'], ['child-fabric1'])

    def test_run_different_parent_fabrics_filtered(self):
        """Test run that child fabrics from different parents are filtered out."""
        parent_fabric = "msd-parent"
        child_fabrics = [
            {'name': 'child-fabric1'}
        ]

        mock_msd_response = {
            'response': {
                'DATA': [
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric1'},
                    {'fabricParent': 'different-parent', 'fabricName': 'other-child1'},
                    {'fabricParent': 'different-parent', 'fabricName': 'other-child2'},
                    {'fabricParent': 'msd-parent', 'fabricName': 'child-fabric2'}
                ]
            }
        }

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_msd_response

            result = action_module.run()

            self.assertFalse(result['failed'])
            # Should only include child fabrics from 'msd-parent', not 'different-parent'
            self.assertEqual(set(result['current_associated_child_fabrics']), {'child-fabric1', 'child-fabric2'})
            self.assertEqual(result['to_be_removed'], ['child-fabric2'])
            self.assertEqual(result['to_be_added'], [])

    def test_run_fabric_data_structure(self):
        """Test run verifies correct handling of fabric data structure."""
        parent_fabric = "msd-parent"
        child_fabrics = [
            {'name': 'fabric-with-name'},
            {'name': 'another-fabric'}
        ]

        mock_msd_response = {
            'response': {
                'DATA': [
                    {'fabricParent': 'msd-parent', 'fabricName': 'existing-fabric'}
                ]
            }
        }

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_msd_response

            result = action_module.run()

            # Verify that fabric names are extracted correctly from the 'name' key
            self.assertEqual(set(result['to_be_added']), {'fabric-with-name', 'another-fabric'})
            self.assertEqual(result['to_be_removed'], ['existing-fabric'])

    def test_run_missing_response_keys(self):
        """Test run when response keys are missing - should handle gracefully or raise appropriate error."""
        parent_fabric = "msd-parent"
        child_fabrics = [
            {'name': 'child-fabric1'}
        ]

        # Missing 'response' or 'DATA' keys should be handled gracefully
        mock_msd_response = {
            'other_key': 'value'
        }

        task_args = {
            'parent_fabric': parent_fabric,
            'child_fabrics': child_fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_msd_response

            # This should raise an AttributeError due to missing keys
            with self.assertRaises(AttributeError):
                result = action_module.run()

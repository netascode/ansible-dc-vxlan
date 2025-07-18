"""
Unit tests for diff_model_changes action plugin.
"""
import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import tempfile
import hashlib

from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.diff_model_changes import ActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.base_test import ActionModuleTestCase


class TestDiffModelChangesActionModule(ActionModuleTestCase):
    """Test cases for diff_model_changes action plugin."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.action_module = self.create_action_module(ActionModule)

    def test_run_previous_file_does_not_exist(self):
        """Test run when previous file does not exist."""
        # Create current file
        current_file = self.create_temp_file("current content")
        previous_file = os.path.join(self.temp_dir, "non_existent_file.txt")

        task_args = {
            'file_name_previous': previous_file,
            'file_name_current': current_file
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertTrue(result['file_data_changed'])
            self.assertFalse(result.get('failed', False))

    def test_run_identical_files(self):
        """Test run when files are identical."""
        content = "identical content"
        current_file = self.create_temp_file(content)
        previous_file = self.create_temp_file(content)

        task_args = {
            'file_name_previous': previous_file,
            'file_name_current': current_file
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['file_data_changed'])
            self.assertFalse(result.get('failed', False))
            # Previous file should be deleted when files are identical
            self.assertFalse(os.path.exists(previous_file))

    def test_run_different_files_no_normalization(self):
        """Test run when files are different and no normalization is needed."""
        previous_content = "previous content"
        current_content = "current content"

        current_file = self.create_temp_file(current_content)
        previous_file = self.create_temp_file(previous_content)

        task_args = {
            'file_name_previous': previous_file,
            'file_name_current': current_file
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertTrue(result['file_data_changed'])
            self.assertFalse(result.get('failed', False))
            # Previous file should still exist when files are different
            self.assertTrue(os.path.exists(previous_file))

    def test_run_files_identical_after_normalization(self):
        """Test run when files are identical after __omit_place_holder__ normalization."""
        previous_content = "key1: __omit_place_holder__abc123\nkey2: value2"
        current_content = "key1: __omit_place_holder__xyz789\nkey2: value2"

        current_file = self.create_temp_file(current_content)
        previous_file = self.create_temp_file(previous_content)

        task_args = {
            'file_name_previous': previous_file,
            'file_name_current': current_file
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['file_data_changed'])
            self.assertFalse(result.get('failed', False))
            # Previous file should be deleted when files are identical after normalization
            self.assertFalse(os.path.exists(previous_file))

    def test_run_files_different_after_normalization(self):
        """Test run when files are still different after normalization."""
        previous_content = "key1: __omit_place_holder__abc123\nkey2: value2"
        current_content = "key1: __omit_place_holder__xyz789\nkey2: different_value"

        current_file = self.create_temp_file(current_content)
        previous_file = self.create_temp_file(previous_content)

        task_args = {
            'file_name_previous': previous_file,
            'file_name_current': current_file
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertTrue(result['file_data_changed'])
            self.assertFalse(result.get('failed', False))
            # Previous file should still exist when files are different
            self.assertTrue(os.path.exists(previous_file))

    def test_run_complex_omit_placeholder_patterns(self):
        """Test run with complex __omit_place_holder__ patterns."""
        previous_content = """
key1: __omit_place_holder__abc123
key2: value2
key3: __omit_place_holder__def456_suffix
nested:
  key4: __omit_place_holder__ghi789
"""
        current_content = """
key1: __omit_place_holder__xyz999
key2: value2
key3: __omit_place_holder__uvw000_suffix
nested:
  key4: __omit_place_holder__rst111
"""

        current_file = self.create_temp_file(current_content)
        previous_file = self.create_temp_file(previous_content)

        task_args = {
            'file_name_previous': previous_file,
            'file_name_current': current_file
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['file_data_changed'])
            self.assertFalse(result.get('failed', False))
            # Previous file should be deleted when files are identical after normalization
            self.assertFalse(os.path.exists(previous_file))

    @patch('builtins.open', side_effect=OSError("Permission denied"))
    def test_run_file_read_error(self, mock_open):
        """Test run when file read fails."""
        current_file = self.create_temp_file("current content")
        previous_file = self.create_temp_file("previous content")

        task_args = {
            'file_name_previous': previous_file,
            'file_name_current': current_file
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            with self.assertRaises(OSError):
                action_module.run()

    def test_run_multiline_content(self):
        """Test run with multiline content containing __omit_place_holder__."""
        previous_content = """line1
line2 with __omit_place_holder__abc123
line3
line4 with __omit_place_holder__def456
line5"""

        current_content = """line1
line2 with __omit_place_holder__xyz789
line3
line4 with __omit_place_holder__uvw000
line5"""

        current_file = self.create_temp_file(current_content)
        previous_file = self.create_temp_file(previous_content)

        task_args = {
            'file_name_previous': previous_file,
            'file_name_current': current_file
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['file_data_changed'])
            self.assertFalse(result.get('failed', False))
            # Previous file should be deleted when files are identical after normalization
            self.assertFalse(os.path.exists(previous_file))

    def test_run_empty_files(self):
        """Test run with empty files."""
        current_file = self.create_temp_file("")
        previous_file = self.create_temp_file("")

        task_args = {
            'file_name_previous': previous_file,
            'file_name_current': current_file
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['file_data_changed'])
            self.assertFalse(result.get('failed', False))
            # Previous file should be deleted when files are identical
            self.assertFalse(os.path.exists(previous_file))


if __name__ == '__main__':
    unittest.main()

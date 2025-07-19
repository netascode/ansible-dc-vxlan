"""
Unit tests for verify_tags action plugin.
"""
import unittest
from unittest.mock import patch

# Try to import from the plugins directory
try:
    from plugins.action.dtc.verify_tags import ActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.dtc.verify_tags import ActionModule
from .base_test import ActionModuleTestCase


class TestVerifyTagsActionModule(ActionModuleTestCase):
    """Test cases for verify_tags action plugin."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.action_module = self.create_action_module(ActionModule)

    def test_run_valid_tags(self):
        """Test run with valid tags."""
        all_tags = ['fabric', 'deploy', 'config', 'validate', 'backup']
        play_tags = ['fabric', 'deploy']

        task_args = {
            'all_tags': all_tags,
            'play_tags': play_tags
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)
            self.assertNotIn('supported_tags', result)

    def test_run_all_tag_in_play_tags(self):
        """Test run when 'all' tag is in play_tags."""
        all_tags = ['fabric', 'deploy', 'config', 'validate', 'backup']
        play_tags = ['all']

        task_args = {
            'all_tags': all_tags,
            'play_tags': play_tags
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)
            self.assertNotIn('supported_tags', result)

    def test_run_all_tag_with_other_tags(self):
        """Test run when 'all' tag is mixed with other tags."""
        all_tags = ['fabric', 'deploy', 'config', 'validate', 'backup']
        play_tags = ['all', 'fabric', 'deploy']

        task_args = {
            'all_tags': all_tags,
            'play_tags': play_tags
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)
            self.assertNotIn('supported_tags', result)

    def test_run_invalid_tag(self):
        """Test run with invalid tag."""
        all_tags = ['fabric', 'deploy', 'config', 'validate', 'backup']
        play_tags = ['fabric', 'invalid_tag']

        task_args = {
            'all_tags': all_tags,
            'play_tags': play_tags
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertTrue(result['failed'])
            self.assertIn("Tag 'invalid_tag' not found in list of supported tags", result['msg'])
            self.assertEqual(result['supported_tags'], all_tags)

    def test_run_multiple_invalid_tags(self):
        """Test run with multiple invalid tags."""
        all_tags = ['fabric', 'deploy', 'config', 'validate', 'backup']
        play_tags = ['fabric', 'invalid_tag1', 'invalid_tag2']

        task_args = {
            'all_tags': all_tags,
            'play_tags': play_tags
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertTrue(result['failed'])
            # Should fail on the last invalid tag encountered (plugin doesn't return early)
            self.assertIn("Tag 'invalid_tag2' not found in list of supported tags", result['msg'])
            self.assertEqual(result['supported_tags'], all_tags)

    def test_run_empty_play_tags(self):
        """Test run with empty play_tags."""
        all_tags = ['fabric', 'deploy', 'config', 'validate', 'backup']
        play_tags = []

        task_args = {
            'all_tags': all_tags,
            'play_tags': play_tags
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)
            self.assertNotIn('supported_tags', result)

    def test_run_empty_all_tags(self):
        """Test run with empty all_tags."""
        all_tags = []
        play_tags = ['fabric']

        task_args = {
            'all_tags': all_tags,
            'play_tags': play_tags
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertTrue(result['failed'])
            self.assertIn("Tag 'fabric' not found in list of supported tags", result['msg'])
            self.assertEqual(result['supported_tags'], all_tags)

    def test_run_case_sensitive_tags(self):
        """Test run with case-sensitive tags."""
        all_tags = ['fabric', 'deploy', 'config', 'validate', 'backup']
        play_tags = ['Fabric', 'DEPLOY']

        task_args = {
            'all_tags': all_tags,
            'play_tags': play_tags
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertTrue(result['failed'])
            # Should fail on the last case-mismatched tag (plugin doesn't return early)
            self.assertIn("Tag 'DEPLOY' not found in list of supported tags", result['msg'])
            self.assertEqual(result['supported_tags'], all_tags)

    def test_run_single_tag_scenarios(self):
        """Test run with single tag scenarios."""
        all_tags = ['fabric', 'deploy', 'config', 'validate', 'backup']

        # Test single valid tag
        play_tags = ['fabric']
        task_args = {
            'all_tags': all_tags,
            'play_tags': play_tags
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)
            self.assertNotIn('supported_tags', result)

    def test_run_duplicate_tags_in_play_tags(self):
        """Test run with duplicate tags in play_tags."""
        all_tags = ['fabric', 'deploy', 'config', 'validate', 'backup']
        play_tags = ['fabric', 'deploy', 'fabric']

        task_args = {
            'all_tags': all_tags,
            'play_tags': play_tags
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)
            self.assertNotIn('supported_tags', result)

    def test_run_duplicate_tags_in_all_tags(self):
        """Test run with duplicate tags in all_tags."""
        all_tags = ['fabric', 'deploy', 'fabric', 'config', 'validate', 'backup']
        play_tags = ['fabric', 'deploy']

        task_args = {
            'all_tags': all_tags,
            'play_tags': play_tags
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            result = action_module.run()

            self.assertFalse(result['failed'])
            self.assertNotIn('msg', result)
            self.assertNotIn('supported_tags', result)

    def test_run_with_none_values(self):
        """Test run with None values."""
        # Test with None all_tags
        task_args = {
            'all_tags': None,
            'play_tags': ['fabric']
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock the run method from parent class
        with patch.object(ActionModule.__bases__[0], 'run') as mock_parent_run:
            mock_parent_run.return_value = {'changed': False}

            with self.assertRaises(TypeError):
                action_module.run()


if __name__ == '__main__':
    unittest.main()

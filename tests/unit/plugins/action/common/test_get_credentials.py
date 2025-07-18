"""Unit tests for get_credentials action plugin."""

import pytest
from unittest.mock import MagicMock, patch, Mock
import copy

# Try to import from the plugins directory
try:
    from plugins.action.common.get_credentials import ActionModule as GetCredentialsActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.common.get_credentials import ActionModule as GetCredentialsActionModule


class TestGetCredentialsActionModule:
    """Test the get_credentials action module."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mock task
        self.mock_task = MagicMock()
        self.mock_task.action = "get_credentials"
        self.mock_task.args = {}

        # Mock other required objects
        self.mock_connection = MagicMock()
        self.mock_play_context = MagicMock()
        self.mock_loader = MagicMock()
        self.mock_templar = MagicMock()
        self.mock_shared_loader_obj = MagicMock()

        # Mock the parent class run method to avoid async issues
        self.mock_parent_run = MagicMock(return_value={})

    def create_action_module(self, task_args=None):
        """Create an action module instance with mocked dependencies."""
        if task_args:
            self.mock_task.args = task_args

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            action_module = GetCredentialsActionModule(
                task=self.mock_task,
                connection=self.mock_connection,
                play_context=self.mock_play_context,
                loader=self.mock_loader,
                templar=self.mock_templar,
                shared_loader_obj=self.mock_shared_loader_obj
            )

        return action_module

    def test_action_module_creation(self):
        """Test that the action module can be created successfully."""
        action_module = self.create_action_module()
        assert action_module is not None
        assert hasattr(action_module, 'run')

    def test_run_method_exists(self):
        """Test that the run method exists and is callable."""
        action_module = self.create_action_module()
        assert hasattr(action_module, 'run')
        assert callable(getattr(action_module, 'run'))

    def test_run_returns_dict(self):
        """Test that the run method returns a dictionary."""
        task_args = {
            'inv_list': [{'name': 'device1'}, {'name': 'device2'}]
        }
        task_vars = {
            'inventory_hostname': 'test-host',
            'hostvars': {
                'test-host': {
                    'ndfc_switch_username': 'admin',
                    'ndfc_switch_password': 'password'
                }
            }
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run(task_vars=task_vars)
            assert isinstance(result, dict)

    def test_run_with_empty_args(self):
        """Test run method with empty arguments."""
        task_args = {
            'inv_list': []
        }
        task_vars = {
            'inventory_hostname': 'test-host',
            'hostvars': {
                'test-host': {
                    'ndfc_switch_username': 'admin',
                    'ndfc_switch_password': 'password'
                }
            }
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run(task_vars=task_vars)
            assert isinstance(result, dict)

    def test_run_with_none_task_vars(self):
        """Test run method with None task_vars."""
        task_args = {
            'inv_list': [{'name': 'device1'}]
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with pytest.raises(TypeError):
                action_module.run(task_vars=None)

    def test_run_with_empty_task_vars(self):
        """Test run method with empty task_vars."""
        task_args = {
            'inv_list': [{'name': 'device1'}]
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with pytest.raises(KeyError):
                action_module.run(task_vars={})

    @patch('ansible.plugins.action.ActionBase.run')
    def test_parent_run_called(self, mock_parent_run):
        """Test that parent run method is called."""
        mock_parent_run.return_value = {}
        task_args = {
            'inv_list': [{'name': 'device1'}]
        }
        task_vars = {
            'inventory_hostname': 'test-host',
            'hostvars': {
                'test-host': {
                    'ndfc_switch_username': 'admin',
                    'ndfc_switch_password': 'password'
                }
            }
        }
        action_module = self.create_action_module(task_args)

        action_module.run(task_vars=task_vars)

        mock_parent_run.assert_called_once()

    def test_run_with_typical_task_vars(self):
        """Test run method with typical task_vars structure."""
        action_module = self.create_action_module()

        task_vars = {
            'inventory_hostname': 'test-host',
            'hostvars': {
                'test-host': {
                    'ansible_host': '192.168.1.1',
                    'ansible_user': 'admin'
                }
            }
        }

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run(task_vars=task_vars)
            assert isinstance(result, dict)

    def test_run_does_not_set_failed_by_default(self):
        """Test that run method doesn't set failed=True by default."""
        task_args = {
            'inv_list': [{'name': 'device1'}]
        }
        task_vars = {
            'inventory_hostname': 'test-host',
            'hostvars': {
                'test-host': {
                    'ndfc_switch_username': 'admin',
                    'ndfc_switch_password': 'password'
                }
            }
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run(task_vars=task_vars)
            assert result.get('failed', False) is False

    def test_inheritance_from_action_base(self):
        """Test that the action module inherits from ActionBase."""
        action_module = self.create_action_module()

        from ansible.plugins.action import ActionBase
        assert isinstance(action_module, ActionBase)

"""Unit tests for read_run_map action plugin."""

import pytest
from unittest.mock import MagicMock, patch, mock_open

# Try to import from the plugins directory
try:
    from plugins.action.common.read_run_map import ActionModule as ReadRunMapActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.common.read_run_map import ActionModule as ReadRunMapActionModule


class TestReadRunMapActionModule:
    """Test the read_run_map action module."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mock task
        self.mock_task = MagicMock()
        self.mock_task.action = "read_run_map"
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
            action_module = ReadRunMapActionModule(
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
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            }
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=False):
                result = action_module.run(task_vars=task_vars)
                assert isinstance(result, dict)
                assert result['diff_run'] is False

    def test_run_with_empty_args(self):
        """Test run method with empty arguments - should fail."""
        task_args = {}
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with pytest.raises(TypeError):
                action_module.run(task_vars=task_vars)

    def test_run_with_none_task_vars(self):
        """Test run method with None task_vars - should fail."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            }
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with pytest.raises(TypeError):
                action_module.run(task_vars=None)

    def test_run_with_empty_task_vars(self):
        """Test run method with empty task_vars - should fail."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            }
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
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            }
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('os.path.exists', return_value=False):
            action_module.run(task_vars=task_vars)

        mock_parent_run.assert_called_once()

    def test_run_with_typical_task_vars(self):
        """Test run method with typical task_vars structure."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            }
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=False):
                result = action_module.run(task_vars=task_vars)
                assert isinstance(result, dict)
                assert result['diff_run'] is False

    def test_run_does_not_set_failed_by_default(self):
        """Test that run method doesn't set failed=True by default."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            }
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=False):
                result = action_module.run(task_vars=task_vars)
                assert result.get('failed', False) is False

    def test_inheritance_from_action_base(self):
        """Test that the action module inherits from ActionBase."""
        action_module = self.create_action_module()

        from ansible.plugins.action import ActionBase
        assert isinstance(action_module, ActionBase)

    def test_run_map_file_exists_all_roles_completed(self):
        """Test when run map file exists and all roles are completed."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            }
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        # Mock YAML data with all roles completed
        yaml_data = {
            'role_validate_completed': True,
            'role_create_completed': True,
            'role_deploy_completed': True,
            'role_remove_completed': True
        }

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', mock_open()):
                    with patch('yaml.safe_load', return_value=yaml_data):
                        result = action_module.run(task_vars=task_vars)
                        assert result['diff_run'] is True

    def test_run_map_file_exists_some_roles_incomplete(self):
        """Test when run map file exists but some roles are incomplete."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            }
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        # Mock YAML data with some roles incomplete
        yaml_data = {
            'role_validate_completed': True,
            'role_create_completed': False,
            'role_deploy_completed': True,
            'role_remove_completed': True
        }

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', mock_open()):
                    with patch('yaml.safe_load', return_value=yaml_data):
                        result = action_module.run(task_vars=task_vars)
                        assert result['diff_run'] is False

    def test_run_map_file_exists_missing_roles(self):
        """Test when run map file exists but has missing role entries."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            }
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        # Mock YAML data with missing roles
        yaml_data = {
            'role_validate_completed': True,
            'role_create_completed': True
            # Missing role_deploy_completed and role_remove_completed
        }

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', mock_open()):
                    with patch('yaml.safe_load', return_value=yaml_data):
                        result = action_module.run(task_vars=task_vars)
                        assert result['diff_run'] is False

    def test_run_map_file_does_not_exist(self):
        """Test when run map file does not exist."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            }
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=False):
                result = action_module.run(task_vars=task_vars)
                assert result['diff_run'] is False

    def test_dtc_role_path_handling(self):
        """Test special handling for 'dtc' in role_path."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            }
        }
        task_vars = {
            'role_path': '/path/to/dtc/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=False):
                with patch('os.path.dirname') as mock_dirname:
                    mock_dirname.side_effect = ['/path/to/dtc', '/path/to']
                    result = action_module.run(task_vars=task_vars)
                    assert result['diff_run'] is False

    def test_regular_role_path_handling(self):
        """Test regular role path handling without 'dtc'."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            }
        }
        task_vars = {
            'role_path': '/path/to/regular/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=False):
                with patch('os.path.dirname') as mock_dirname:
                    mock_dirname.return_value = '/path/to/regular'
                    result = action_module.run(task_vars=task_vars)
                    assert result['diff_run'] is False

    def test_fabric_name_in_file_path(self):
        """Test that fabric name is correctly used in file path."""
        fabric_name = 'my-special-fabric'
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': fabric_name
                    }
                }
            }
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists') as mock_exists:
                mock_exists.return_value = False
                result = action_module.run(task_vars=task_vars)

                # Check that the fabric name was used in the file path
                expected_path = f'/path/to/validate/files/{fabric_name}_run_map.yml'
                mock_exists.assert_called_with(expected_path)
                assert result['diff_run'] is False

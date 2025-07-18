"""Unit tests for run_map action plugin."""

import pytest
from unittest.mock import MagicMock, patch, mock_open

# Try to import from the plugins directory
try:
    from plugins.action.common.run_map import ActionModule as RunMapActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.common.run_map import ActionModule as RunMapActionModule


class TestRunMapActionModule:
    """Test the run_map action module."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mock task
        self.mock_task = MagicMock()
        self.mock_task.action = "run_map"
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
            action_module = RunMapActionModule(
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
            },
            'stage': 'starting_execution'
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', mock_open()):
                    result = action_module.run(task_vars=task_vars)
                    assert isinstance(result, dict)
                    assert result['failed'] is False

    def test_run_with_empty_args(self):
        """Test run method with empty arguments - should fail."""
        task_args = {}
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with pytest.raises(KeyError):
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
            },
            'stage': 'starting_execution'
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
            },
            'stage': 'starting_execution'
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
            },
            'stage': 'starting_execution'
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open()):
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
            },
            'stage': 'starting_execution'
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', mock_open()):
                    result = action_module.run(task_vars=task_vars)
                    assert isinstance(result, dict)
                    assert result['failed'] is False

    def test_run_does_not_set_failed_by_default(self):
        """Test that run method doesn't set failed=True by default."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            },
            'stage': 'starting_execution'
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', mock_open()):
                    result = action_module.run(task_vars=task_vars)
                    assert result['failed'] is False

    def test_inheritance_from_action_base(self):
        """Test that the action module inherits from ActionBase."""
        action_module = self.create_action_module()

        from ansible.plugins.action import ActionBase
        assert isinstance(action_module, ActionBase)

    def test_starting_execution_stage(self):
        """Test starting_execution stage creates initial run map."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            },
            'stage': 'starting_execution'
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', mock_open()) as mock_file:
                    with patch('yaml.dump') as mock_yaml_dump:
                        result = action_module.run(task_vars=task_vars)

                        # Check that file was opened for writing
                        mock_file.assert_called()
                        # Check that yaml.dump was called
                        mock_yaml_dump.assert_called_once()

                        # Check that all role completion flags are set to False
                        call_args = mock_yaml_dump.call_args[0]
                        updated_run_map = call_args[0]
                        assert updated_run_map['role_validate_completed'] is False
                        assert updated_run_map['role_create_completed'] is False
                        assert updated_run_map['role_deploy_completed'] is False
                        assert updated_run_map['role_remove_completed'] is False
                        assert 'time_stamp' in updated_run_map

    def test_role_validate_completed_stage(self):
        """Test role_validate_completed stage updates run map."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            },
            'stage': 'role_validate_completed'
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        # Mock existing run map data
        existing_data = {
            'role_validate_completed': False,
            'role_create_completed': False,
            'role_deploy_completed': False,
            'role_remove_completed': False
        }

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', mock_open()):
                    with patch('yaml.safe_load', return_value=existing_data):
                        with patch('yaml.dump') as mock_yaml_dump:
                            result = action_module.run(task_vars=task_vars)

                            # Check that role_validate_completed was set to True
                            call_args = mock_yaml_dump.call_args[0]
                            updated_run_map = call_args[0]
                            assert updated_run_map['role_validate_completed'] is True
                            assert updated_run_map['role_create_completed'] is False
                            assert updated_run_map['role_deploy_completed'] is False
                            assert updated_run_map['role_remove_completed'] is False

    def test_role_create_completed_stage(self):
        """Test role_create_completed stage updates run map."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            },
            'stage': 'role_create_completed'
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        existing_data = {
            'role_validate_completed': True,
            'role_create_completed': False,
            'role_deploy_completed': False,
            'role_remove_completed': False
        }

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', mock_open()):
                    with patch('yaml.safe_load', return_value=existing_data):
                        with patch('yaml.dump') as mock_yaml_dump:
                            result = action_module.run(task_vars=task_vars)

                            call_args = mock_yaml_dump.call_args[0]
                            updated_run_map = call_args[0]
                            assert updated_run_map['role_validate_completed'] is True
                            assert updated_run_map['role_create_completed'] is True
                            assert updated_run_map['role_deploy_completed'] is False
                            assert updated_run_map['role_remove_completed'] is False

    def test_role_deploy_completed_stage(self):
        """Test role_deploy_completed stage updates run map."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            },
            'stage': 'role_deploy_completed'
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        existing_data = {
            'role_validate_completed': True,
            'role_create_completed': True,
            'role_deploy_completed': False,
            'role_remove_completed': False
        }

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', mock_open()):
                    with patch('yaml.safe_load', return_value=existing_data):
                        with patch('yaml.dump') as mock_yaml_dump:
                            result = action_module.run(task_vars=task_vars)

                            call_args = mock_yaml_dump.call_args[0]
                            updated_run_map = call_args[0]
                            assert updated_run_map['role_validate_completed'] is True
                            assert updated_run_map['role_create_completed'] is True
                            assert updated_run_map['role_deploy_completed'] is True
                            assert updated_run_map['role_remove_completed'] is False

    def test_role_remove_completed_stage(self):
        """Test role_remove_completed stage updates run map."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            },
            'stage': 'role_remove_completed'
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        existing_data = {
            'role_validate_completed': True,
            'role_create_completed': True,
            'role_deploy_completed': True,
            'role_remove_completed': False
        }

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', mock_open()):
                    with patch('yaml.safe_load', return_value=existing_data):
                        with patch('yaml.dump') as mock_yaml_dump:
                            result = action_module.run(task_vars=task_vars)

                            call_args = mock_yaml_dump.call_args[0]
                            updated_run_map = call_args[0]
                            assert updated_run_map['role_validate_completed'] is True
                            assert updated_run_map['role_create_completed'] is True
                            assert updated_run_map['role_deploy_completed'] is True
                            assert updated_run_map['role_remove_completed'] is True

    def test_common_role_path_not_exists(self):
        """Test behavior when common role path doesn't exist."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            },
            'stage': 'starting_execution'
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=False):
                # The module should still try to write the file even if directory doesn't exist
                # So we need to mock the file operations
                with patch('builtins.open', mock_open()):
                    result = action_module.run(task_vars=task_vars)
                    assert result['failed'] is True

    def test_dtc_role_path_handling(self):
        """Test special handling for 'dtc' in role_path."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            },
            'stage': 'starting_execution'
        }
        task_vars = {
            'role_path': '/path/to/dtc/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', mock_open()):
                    with patch('yaml.dump'):
                        result = action_module.run(task_vars=task_vars)
                        assert result['failed'] is False

    def test_file_header_written(self):
        """Test that the auto-generated file header is written."""
        task_args = {
            'model_data': {
                'vxlan': {
                    'fabric': {
                        'name': 'test-fabric'
                    }
                }
            },
            'stage': 'starting_execution'
        }
        task_vars = {
            'role_path': '/path/to/role'
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', mock_open()) as mock_file:
                    with patch('yaml.dump'):
                        result = action_module.run(task_vars=task_vars)

                        # Check that write was called with the header
                        mock_file.return_value.write.assert_called_with(
                            "### This File Is Auto Generated, Do Not Edit ###\n"
                        )

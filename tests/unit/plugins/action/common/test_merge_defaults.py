"""Unit tests for merge_defaults action plugin."""

from unittest.mock import MagicMock, patch

# Try to import from the plugins directory
try:
    from plugins.action.common.merge_defaults import ActionModule as MergeDefaultsActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.common.merge_defaults import ActionModule as MergeDefaultsActionModule


class TestMergeDefaultsActionModule:
    """Test the merge_defaults action module."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mock task
        self.mock_task = MagicMock()
        self.mock_task.action = "merge_defaults"
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
            action_module = MergeDefaultsActionModule(
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
            'factory_defaults': {'default_key': 'default_value'},
            'model_data': {'key': 'value'}
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert isinstance(result, dict)

    def test_run_with_empty_args(self):
        """Test run method with empty arguments."""
        task_args = {
            'factory_defaults': {},
            'model_data': None
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert isinstance(result, dict)
            assert result['defaults'] == {}

    def test_run_with_none_task_vars(self):
        """Test run method with None task_vars."""
        task_args = {
            'factory_defaults': {'default_key': 'default_value'},
            'model_data': None
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run(task_vars=None)
            assert isinstance(result, dict)
            assert result['defaults'] == {'default_key': 'default_value'}

    def test_run_with_empty_task_vars(self):
        """Test run method with empty task_vars."""
        task_args = {
            'factory_defaults': {'default_key': 'default_value'},
            'model_data': {}
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run(task_vars={})
            assert isinstance(result, dict)
            assert result['defaults'] == {'default_key': 'default_value'}

    @patch('ansible.plugins.action.ActionBase.run')
    def test_parent_run_called(self, mock_parent_run):
        """Test that parent run method is called."""
        mock_parent_run.return_value = {}
        task_args = {
            'factory_defaults': {'default_key': 'default_value'},
            'model_data': {'key': 'value'}
        }
        action_module = self.create_action_module(task_args)

        action_module.run()

        mock_parent_run.assert_called_once()

    def test_run_with_typical_task_vars(self):
        """Test run method with typical task_vars structure."""
        task_args = {
            'factory_defaults': {
                'setting1': 'default1',
                'setting2': 'default2',
                'nested': {
                    'sub1': 'default_sub1',
                    'sub2': 'default_sub2'
                }
            },
            'model_data': {
                'defaults': {
                    'setting1': 'custom1',
                    'setting3': 'custom3',
                    'nested': {
                        'sub1': 'custom_sub1',
                        'sub3': 'custom_sub3'
                    }
                }
            }
        }
        action_module = self.create_action_module(task_args)

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
            # Check that defaults were merged correctly
            expected_defaults = {
                'setting1': 'custom1',  # Overridden by custom
                'setting2': 'default2',  # Kept from factory
                'setting3': 'custom3',   # Added from custom
                'nested': {
                    'sub1': 'custom_sub1',  # Overridden by custom
                    'sub2': 'default_sub2',  # Kept from factory
                    'sub3': 'custom_sub3'    # Added from custom
                }
            }
            assert result['defaults'] == expected_defaults

    def test_run_does_not_set_failed_by_default(self):
        """Test that run method doesn't set failed=True by default."""
        task_args = {
            'factory_defaults': {'default_key': 'default_value'},
            'model_data': None
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert result.get('failed', False) is False

    def test_inheritance_from_action_base(self):
        """Test that the action module inherits from ActionBase."""
        action_module = self.create_action_module()

        from ansible.plugins.action import ActionBase
        assert isinstance(action_module, ActionBase)

    def test_merge_dicts_function(self):
        """Test the merge_dicts function directly."""
        from plugins.action.common.merge_defaults import merge_dicts

        d1 = {
            'a': 1,
            'b': {'x': 10, 'y': 20},
            'c': 'original'
        }
        d2 = {
            'b': {'y': 25, 'z': 30},
            'd': 'new'
        }

        result = merge_dicts(d1, d2)

        expected = {
            'a': 1,
            'b': {'x': 10, 'y': 25, 'z': 30},
            'c': 'original',
            'd': 'new'
        }

        assert result == expected

    def test_merge_with_none_model_data(self):
        """Test merging when model_data is None."""
        task_args = {
            'factory_defaults': {'key1': 'value1', 'key2': 'value2'},
            'model_data': None
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert result['defaults'] == {'key1': 'value1', 'key2': 'value2'}

    def test_merge_with_empty_model_data(self):
        """Test merging when model_data is empty dict."""
        task_args = {
            'factory_defaults': {'key1': 'value1', 'key2': 'value2'},
            'model_data': {}
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert result['defaults'] == {'key1': 'value1', 'key2': 'value2'}

    def test_merge_with_model_data_no_defaults(self):
        """Test merging when model_data has no defaults key."""
        task_args = {
            'factory_defaults': {'key1': 'value1', 'key2': 'value2'},
            'model_data': {'other_key': 'other_value'}
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert result['defaults'] == {'key1': 'value1', 'key2': 'value2'}

    def test_merge_with_empty_factory_defaults(self):
        """Test merging when factory_defaults is empty."""
        task_args = {
            'factory_defaults': {},
            'model_data': {
                'defaults': {'custom1': 'value1', 'custom2': 'value2'}
            }
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert result['defaults'] == {'custom1': 'value1', 'custom2': 'value2'}

    def test_merge_deep_nested_structures(self):
        """Test merging with deeply nested structures."""
        task_args = {
            'factory_defaults': {
                'level1': {
                    'level2': {
                        'level3': {
                            'setting1': 'default1',
                            'setting2': 'default2'
                        }
                    }
                }
            },
            'model_data': {
                'defaults': {
                    'level1': {
                        'level2': {
                            'level3': {
                                'setting1': 'custom1',
                                'setting3': 'custom3'
                            }
                        }
                    }
                }
            }
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            expected = {
                'level1': {
                    'level2': {
                        'level3': {
                            'setting1': 'custom1',
                            'setting2': 'default2',
                            'setting3': 'custom3'
                        }
                    }
                }
            }
            assert result['defaults'] == expected

    def test_merge_overrides_non_dict_values(self):
        """Test that non-dict values are completely overridden."""
        task_args = {
            'factory_defaults': {
                'setting1': 'original_string',
                'setting2': ['original', 'list']
            },
            'model_data': {
                'defaults': {
                    'setting1': 'new_string',
                    'setting2': ['new', 'list', 'items']
                }
            }
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            expected = {
                'setting1': 'new_string',
                'setting2': ['new', 'list', 'items']
            }
            assert result['defaults'] == expected

    def test_result_structure(self):
        """Test that the result has the expected structure."""
        task_args = {
            'factory_defaults': {'key': 'value'},
            'model_data': None
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert 'failed' in result
            assert 'msg' in result
            assert 'defaults' in result
            assert result['failed'] is False
            assert result['msg'] is None

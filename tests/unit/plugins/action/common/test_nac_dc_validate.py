"""Unit tests for nac_dc_validate action plugin."""

import pytest
from unittest.mock import MagicMock, patch, Mock
import copy
import os

# Try to import from the plugins directory
try:
    from plugins.action.common.nac_dc_validate import ActionModule as NacDcValidateActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.common.nac_dc_validate import ActionModule as NacDcValidateActionModule


class TestNacDcValidateActionModule:
    """Test the nac_dc_validate action module."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mock task
        self.mock_task = MagicMock()
        self.mock_task.action = "nac_dc_validate"
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
            action_module = NacDcValidateActionModule(
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
    
    def test_inheritance_from_action_base(self):
        """Test that the action module inherits from ActionBase."""
        action_module = self.create_action_module()
        
        from ansible.plugins.action import ActionBase
        assert isinstance(action_module, ActionBase)
    
    # New comprehensive tests for missing coverage areas
    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.load_yaml_files')
    @patch('plugins.action.common.nac_dc_validate.data_model_key_check')
    def test_mcf_fabric_type(self, mock_key_check, mock_load_yaml, mock_listdir, mock_exists, mock_parent_run):
        """Test validation with MCF fabric type."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        # Mock data model
        mock_data = {
            'vxlan': {
                'fabric': {
                    'type': 'MCF'
                }
            }
        }
        mock_load_yaml.return_value = mock_data
        mock_key_check.return_value = {
            'keys_found': ['fabric'],
            'keys_data': ['fabric']
        }
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules/',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/path/to/rules'
        }
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = []
            mock_validator.return_value = mock_validator_instance
            
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            assert result['failed'] is False
            # MCF should use multisite rules
            mock_validator.assert_called_with('/path/to/schema.yaml', '/path/to/rules/multisite/')
    
    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.load_yaml_files')
    @patch('plugins.action.common.nac_dc_validate.data_model_key_check')
    def test_isn_fabric_type(self, mock_key_check, mock_load_yaml, mock_listdir, mock_exists, mock_parent_run):
        """Test validation with ISN fabric type."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        # Mock data model
        mock_data = {
            'vxlan': {
                'fabric': {
                    'type': 'ISN'
                }
            }
        }
        mock_load_yaml.return_value = mock_data
        mock_key_check.return_value = {
            'keys_found': ['fabric'],
            'keys_data': ['fabric']
        }
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules/',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/path/to/rules'
        }
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = []
            mock_validator.return_value = mock_validator_instance
            
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            assert result['failed'] is False
            # ISN should use isn rules
            mock_validator.assert_called_with('/path/to/schema.yaml', '/path/to/rules/isn/')
    
    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.load_yaml_files')
    @patch('plugins.action.common.nac_dc_validate.data_model_key_check')
    def test_external_fabric_type(self, mock_key_check, mock_load_yaml, mock_listdir, mock_exists, mock_parent_run):
        """Test validation with External fabric type."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        # Mock data model
        mock_data = {
            'vxlan': {
                'fabric': {
                    'type': 'External'
                }
            }
        }
        mock_load_yaml.return_value = mock_data
        mock_key_check.return_value = {
            'keys_found': ['fabric'],
            'keys_data': ['fabric']
        }
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules/',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/path/to/rules'
        }
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = []
            mock_validator.return_value = mock_validator_instance
            
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            assert result['failed'] is False
            # External should use external rules
            mock_validator.assert_called_with('/path/to/schema.yaml', '/path/to/rules/external/')
    
    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.load_yaml_files')
    @patch('plugins.action.common.nac_dc_validate.data_model_key_check')
    @patch('plugins.action.common.nac_dc_validate.display')
    def test_deprecated_global_fabric_type_mcf(self, mock_display, mock_key_check, mock_load_yaml, mock_listdir, mock_exists, mock_parent_run):
        """Test validation with deprecated vxlan.global.fabric_type set to MCF."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        # Mock data model with deprecated structure
        mock_data = {
            'vxlan': {
                'global': {
                    'fabric_type': 'MCF'
                }
            }
        }
        mock_load_yaml.return_value = mock_data
        
        # First call returns no fabric keys, second call returns global keys
        mock_key_check.side_effect = [
            {'keys_found': [], 'keys_data': []},
            {'keys_found': ['global'], 'keys_data': ['global']}
        ]
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules/',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/path/to/rules'
        }
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = []
            mock_validator.return_value = mock_validator_instance
            
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            assert result['failed'] is False
            mock_display.deprecated.assert_called_once()
            # MCF should use multisite rules
            mock_validator.assert_called_with('/path/to/schema.yaml', '/path/to/rules/multisite/')
    
    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.load_yaml_files')
    @patch('plugins.action.common.nac_dc_validate.data_model_key_check')
    @patch('plugins.action.common.nac_dc_validate.display')
    def test_deprecated_global_fabric_type_isn(self, mock_display, mock_key_check, mock_load_yaml, mock_listdir, mock_exists, mock_parent_run):
        """Test validation with deprecated vxlan.global.fabric_type set to ISN."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        # Mock data model with deprecated structure
        mock_data = {
            'vxlan': {
                'global': {
                    'fabric_type': 'ISN'
                }
            }
        }
        mock_load_yaml.return_value = mock_data
        
        # First call returns no fabric keys, second call returns global keys
        mock_key_check.side_effect = [
            {'keys_found': [], 'keys_data': []},
            {'keys_found': ['global'], 'keys_data': ['global']}
        ]
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules/',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/path/to/rules'
        }
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = []
            mock_validator.return_value = mock_validator_instance
            
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            assert result['failed'] is False
            mock_display.deprecated.assert_called_once()
            # ISN should use isn rules
            mock_validator.assert_called_with('/path/to/schema.yaml', '/path/to/rules/isn/')
    
    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.load_yaml_files')
    @patch('plugins.action.common.nac_dc_validate.data_model_key_check')
    @patch('plugins.action.common.nac_dc_validate.display')
    def test_deprecated_global_fabric_type_external(self, mock_display, mock_key_check, mock_load_yaml, mock_listdir, mock_exists, mock_parent_run):
        """Test validation with deprecated vxlan.global.fabric_type set to External (which uses isn rules)."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        # Mock data model with deprecated structure
        mock_data = {
            'vxlan': {
                'global': {
                    'fabric_type': 'External'
                }
            }
        }
        mock_load_yaml.return_value = mock_data
        
        # First call returns no fabric keys, second call returns global keys
        mock_key_check.side_effect = [
            {'keys_found': [], 'keys_data': []},
            {'keys_found': ['global'], 'keys_data': ['global']}
        ]
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules/',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/path/to/rules'
        }
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = []
            mock_validator.return_value = mock_validator_instance
            
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            assert result['failed'] is False
            mock_display.deprecated.assert_called_once()
            # External should use isn rules in deprecated mode
            mock_validator.assert_called_with('/path/to/schema.yaml', '/path/to/rules/isn/')
    
    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.load_yaml_files')
    @patch('plugins.action.common.nac_dc_validate.data_model_key_check')
    @patch('plugins.action.common.nac_dc_validate.display')
    def test_deprecated_global_fabric_type_unsupported(self, mock_display, mock_key_check, mock_load_yaml, mock_listdir, mock_exists, mock_parent_run):
        """Test validation failure with deprecated vxlan.global.fabric_type set to unsupported type."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        # Mock data model with deprecated structure and unsupported type
        mock_data = {
            'vxlan': {
                'global': {
                    'fabric_type': 'UNSUPPORTED'
                }
            }
        }
        mock_load_yaml.return_value = mock_data
        
        # First call returns no fabric keys, second call returns global keys
        mock_key_check.side_effect = [
            {'keys_found': [], 'keys_data': []},
            {'keys_found': ['global'], 'keys_data': ['global']}
        ]
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/path/to/rules'
        }
        
        action_module = self.create_action_module(task_args)
        result = action_module.run(task_vars=task_vars)
        
        assert result['failed'] is True
        assert 'is not a supported fabric type' in result['msg']
        mock_display.deprecated.assert_called_once()
    
    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.load_yaml_files')
    @patch('plugins.action.common.nac_dc_validate.data_model_key_check')
    @patch('plugins.action.common.nac_dc_validate.display')
    def test_deprecated_global_missing_fabric_type(self, mock_display, mock_key_check, mock_load_yaml, mock_listdir, mock_exists, mock_parent_run):
        """Test validation failure when deprecated vxlan.global.fabric_type is missing."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        # Mock data model with deprecated structure but missing fabric_type
        mock_data = {
            'vxlan': {
                'global': {
                    'name': 'test-fabric'
                }
            }
        }
        mock_load_yaml.return_value = mock_data
        
        # First call returns no fabric keys, second call returns global keys
        mock_key_check.side_effect = [
            {'keys_found': [], 'keys_data': []},
            {'keys_found': ['global'], 'keys_data': ['global']}
        ]
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules/',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/path/to/rules'
        }
        
        action_module = self.create_action_module(task_args)
        result = action_module.run(task_vars=task_vars)
        
        assert result['failed'] is True
        assert 'is not defined in the data model' in result['msg']
        # The deprecated warning is only called if fabric_type is present
        mock_display.deprecated.assert_not_called()
    
    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_rules_directory_with_only_gitkeep(self, mock_listdir, mock_exists, mock_parent_run):
        """Test warning when rules directory contains only .gitkeep file."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        
        def listdir_side_effect(path):
            if 'rules' in path:
                return ['.gitkeep']  # Only .gitkeep file
            return ['data.yaml']
        
        mock_listdir.side_effect = listdir_side_effect
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/different/role/path'
        }
        
        with patch('plugins.action.common.nac_dc_validate.display') as mock_display:
            with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
                mock_validator_instance = MagicMock()
                mock_validator_instance.errors = []
                mock_validator.return_value = mock_validator_instance
                
                action_module = self.create_action_module(task_args)
                result = action_module.run(task_vars=task_vars)
                
                assert result['failed'] is False
                # Should have generated warning about empty rules directory
                mock_display.warning.assert_called()
                warning_calls = [call.args[0] for call in mock_display.warning.call_args_list]
                assert any('exists but is empty' in call for call in warning_calls)
    
    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_validation_with_only_semantics_check(self, mock_listdir, mock_exists, mock_parent_run):
        """Test validation when only semantics check is performed (no schema)."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        task_args = {
            'schema': None,  # No schema provided
            'rules': '/path/to/rules',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/different/role/path'
        }
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = []
            mock_validator.return_value = mock_validator_instance
            
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            assert result['failed'] is False
            # Should not call validate_syntax since no schema
            mock_validator_instance.validate_syntax.assert_not_called()
            # Should call validate_semantics since rules exist
            mock_validator_instance.validate_semantics.assert_called_once()
    
    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_validation_with_only_syntax_check(self, mock_listdir, mock_exists, mock_parent_run):
        """Test validation when only syntax check is performed (no rules)."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules/',  # Provide rules path
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/different/role/path'  # Different role path so rules check fails
        }
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = []
            mock_validator.return_value = mock_validator_instance
            
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            assert result['failed'] is False
            # Should call validate_syntax since schema exists
            mock_validator_instance.validate_syntax.assert_called_once()
            # Should call validate_semantics since rules path is provided (custom enhanced rules)
            mock_validator_instance.validate_semantics.assert_called_once()
    
    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_validation_early_exit_on_error(self, mock_listdir, mock_exists, mock_parent_run):
        """Test that validation exits early on first error in rules loop."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/different/role/path'  # Custom rules path
        }
        
        # Mock multiple validator calls to test early exit
        validator_instances = []
        
        def create_validator_instance(*args, **kwargs):
            instance = MagicMock()
            validator_instances.append(instance)
            if len(validator_instances) == 1:
                # First validator has errors - should cause early exit
                instance.errors = ['First error']
            else:
                # Second validator (should not be reached)
                instance.errors = []
            return instance
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator', side_effect=create_validator_instance):
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            assert result['failed'] is True
            assert 'First error' in result['msg']
            # Should only create one validator instance due to early exit
            assert len(validator_instances) == 1
    
    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_missing_task_args(self, mock_listdir, mock_exists, mock_parent_run):
        """Test handling of missing task arguments."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        # Missing required arguments
        task_args = {}
        
        task_vars = {
            'role_path': '/path/to/role'
        }
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = []
            mock_validator.return_value = mock_validator_instance
            
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            # Should handle missing arguments gracefully
            assert isinstance(result, dict)
            assert 'failed' in result
    
    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_none_task_vars(self, mock_listdir, mock_exists, mock_parent_run):
        """Test handling of None task_vars."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': None,  # No rules provided to avoid role_path access
            'mdata': '/path/to/data'
        }
        
        action_module = self.create_action_module(task_args)
        
        # Call with None task_vars - should handle gracefully
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = []
            mock_validator.return_value = mock_validator_instance
            
            result = action_module.run(task_vars=None)
            
            # Should not crash with None task_vars
            assert isinstance(result, dict)
            assert 'failed' in result

    # Additional tests for 100% coverage
    def test_iac_validate_import_error(self):
        """Test handling of iac-validate import error."""
        from ansible.errors import AnsibleError
        
        with patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', ImportError("iac-validate not found")):
            task_args = {
                'schema': '/path/to/schema.yaml',
                'rules': '/path/to/rules',
                'mdata': '/path/to/data'
            }
            
            task_vars = {
                'role_path': '/path/to/role'
            }
            
            # Mock the parent run method to bypass async issues
            with patch('ansible.plugins.action.ActionBase.run', return_value={}):
                action_module = self.create_action_module(task_args)
                
                # Should raise AnsibleError when iac-validate is not installed
                with pytest.raises(AnsibleError, match="iac-validate not found"):
                    action_module.run(task_vars=task_vars)

    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.display')
    def test_schema_empty_string_warning(self, mock_display, mock_listdir, mock_exists, mock_parent_run):
        """Test warning when schema is empty string."""
        mock_parent_run.return_value = {}
        mock_exists.side_effect = lambda path: path != ""  # Empty string doesn't exist
        mock_listdir.return_value = ['data.yaml']
        
        task_args = {
            'schema': '',  # Empty string
            'rules': '/path/to/rules',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/different/role/path'
        }
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = []
            mock_validator.return_value = mock_validator_instance
            
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            # Should generate warning for empty schema
            mock_display.warning.assert_called()
            warning_calls = [call[0][0] for call in mock_display.warning.call_args_list]
            assert any('does not appear to exist' in call for call in warning_calls)

    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.display')
    def test_rules_empty_string_warning(self, mock_display, mock_listdir, mock_exists, mock_parent_run):
        """Test warning when rules is empty string."""
        mock_parent_run.return_value = {}
        mock_exists.side_effect = lambda path: path != ""  # Empty string doesn't exist
        mock_listdir.return_value = ['data.yaml']
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '',  # Empty string
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/different/role/path'
        }
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = []
            mock_validator.return_value = mock_validator_instance
            
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            # Should generate warning for empty rules
            mock_display.warning.assert_called()
            warning_calls = [call[0][0] for call in mock_display.warning.call_args_list]
            assert any('does not appear to exist' in call for call in warning_calls)

    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_data_directory_not_exists(self, mock_listdir, mock_exists, mock_parent_run):
        """Test when data directory doesn't exist."""
        mock_parent_run.return_value = {}
        mock_exists.side_effect = lambda path: '/path/to/data' not in path
        mock_listdir.return_value = ['data.yaml']  # For other paths
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/path/to/role'
        }
        
        action_module = self.create_action_module(task_args)
        result = action_module.run(task_vars=task_vars)
        
        assert result['failed'] is True
        assert 'does not appear to exist' in result['msg']

    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_data_directory_empty(self, mock_listdir, mock_exists, mock_parent_run):
        """Test when data directory is empty."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = []  # Empty directory
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/path/to/role'
        }
        
        action_module = self.create_action_module(task_args)
        result = action_module.run(task_vars=task_vars)
        
        assert result['failed'] is True
        assert 'is empty' in result['msg']

    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.load_yaml_files')
    @patch('plugins.action.common.nac_dc_validate.data_model_key_check')
    def test_vxlan_evpn_fabric_type(self, mock_key_check, mock_load_yaml, mock_listdir, mock_exists, mock_parent_run):
        """Test validation with VXLAN_EVPN fabric type."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        # Mock data model
        mock_data = {
            'vxlan': {
                'fabric': {
                    'type': 'VXLAN_EVPN'
                }
            }
        }
        mock_load_yaml.return_value = mock_data
        mock_key_check.return_value = {
            'keys_found': ['fabric'],
            'keys_data': ['fabric']
        }
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules/',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/path/to/rules'
        }
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = []
            mock_validator.return_value = mock_validator_instance
            
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            assert result['failed'] is False
            mock_validator.assert_called_with('/path/to/schema.yaml', '/path/to/rules/ibgp_vxlan/')

    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.load_yaml_files')
    @patch('plugins.action.common.nac_dc_validate.data_model_key_check')
    @patch('plugins.action.common.nac_dc_validate.display')
    def test_deprecated_vxlan_evpn_fabric_type(self, mock_display, mock_key_check, mock_load_yaml, mock_listdir, mock_exists, mock_parent_run):
        """Test validation with deprecated VXLAN_EVPN fabric type."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        # Mock data model with deprecated structure
        mock_data = {
            'vxlan': {
                'global': {
                    'fabric_type': 'VXLAN_EVPN'
                }
            }
        }
        mock_load_yaml.return_value = mock_data
        
        # First call returns no fabric keys, second call returns global keys
        mock_key_check.side_effect = [
            {'keys_found': [], 'keys_data': []},
            {'keys_found': ['global'], 'keys_data': ['global']}
        ]
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules/',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/path/to/rules'
        }
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = []
            mock_validator.return_value = mock_validator_instance
            
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            assert result['failed'] is False
            mock_display.deprecated.assert_called_once()
            mock_validator.assert_called_with('/path/to/schema.yaml', '/path/to/rules/ibgp_vxlan/')

    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.load_yaml_files')
    @patch('plugins.action.common.nac_dc_validate.data_model_key_check')
    def test_no_fabric_or_global_keys(self, mock_key_check, mock_load_yaml, mock_listdir, mock_exists, mock_parent_run):
        """Test validation when no fabric or global keys are found - fallback to custom rules."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        # Mock data model with no fabric or global keys
        mock_data = {
            'vxlan': {
                'other': {
                    'data': 'value'
                }
            }
        }
        mock_load_yaml.return_value = mock_data
        
        # Both calls return no fabric/global keys
        mock_key_check.side_effect = [
            {'keys_found': [], 'keys_data': []},
            {'keys_found': [], 'keys_data': []}
        ]
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules/',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/different/role/path'  # Different path to trigger else block
        }
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = []
            mock_validator.return_value = mock_validator_instance
            
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            # Should succeed as it falls back to custom enhanced rules
            assert result['failed'] is False
            # Should use custom enhanced rules path
            mock_validator.assert_called_with('/path/to/schema.yaml', '/path/to/rules/')

    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.DEFAULT_SCHEMA', '/default/schema.yaml')
    def test_empty_schema_default_handling(self, mock_listdir, mock_exists, mock_parent_run):
        """Test handling of empty schema with DEFAULT_SCHEMA."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        task_args = {
            'schema': '',  # Empty string should use DEFAULT_SCHEMA
            'rules': '/path/to/rules/',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/different/role/path'
        }
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = []
            mock_validator.return_value = mock_validator_instance
            
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            # Should use DEFAULT_SCHEMA when schema is empty
            mock_validator.assert_called_with('/default/schema.yaml', '/path/to/rules/')

    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_validator_with_errors(self, mock_listdir, mock_exists, mock_parent_run):
        """Test validator returning errors."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules/',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/different/role/path'
        }
        
        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.errors = ['Error 1', 'Error 2']
            mock_validator.return_value = mock_validator_instance
            
            action_module = self.create_action_module(task_args)
            result = action_module.run(task_vars=task_vars)
            
            assert result['failed'] is True
            assert 'Error 1' in result['msg']
            assert 'Error 2' in result['msg']

    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.load_yaml_files')
    @patch('plugins.action.common.nac_dc_validate.data_model_key_check')
    def test_no_global_keys_found(self, mock_key_check, mock_load_yaml, mock_listdir, mock_exists, mock_parent_run):
        """Test when no global keys are found after fabric check fails."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        # Mock data model with no fabric or global keys
        mock_data = {
            'vxlan': {
                'other': {
                    'data': 'value'
                }
            }
        }
        mock_load_yaml.return_value = mock_data
        
        # First call returns no fabric keys, second call returns no global keys either
        mock_key_check.side_effect = [
            {'keys_found': [], 'keys_data': []},  # No fabric keys
            {'keys_found': [], 'keys_data': []}   # No global keys
        ]
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules/',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/path/to/rules'  # Role path in rules to trigger main logic
        }
        
        action_module = self.create_action_module(task_args)
        result = action_module.run(task_vars=task_vars)
        
        # Should succeed because when no fabric/global keys are found, it just continues
        # without running any validation rules
        assert result['failed'] is False

    def test_iac_validate_import_success(self):
        """Test successful import of iac-validate (covers else clause)."""
        # This test covers the successful import path (lines 35-36)
        with patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None):
            task_args = {
                'schema': '/path/to/schema.yaml',
                'rules': '/path/to/rules/',
                'mdata': '/path/to/data'
            }
            
            task_vars = {
                'role_path': '/different/role/path'
            }
            
            with patch('ansible.plugins.action.ActionBase.run', return_value={}):
                with patch('os.path.exists', return_value=True):
                    with patch('os.listdir', return_value=['data.yaml']):
                        with patch('plugins.action.common.nac_dc_validate.iac_validate.validator.Validator') as mock_validator:
                            mock_validator_instance = MagicMock()
                            mock_validator_instance.errors = []
                            mock_validator.return_value = mock_validator_instance
                            
                            action_module = self.create_action_module(task_args)
                            result = action_module.run(task_vars=task_vars)
                            
            # Should succeed without import error
            assert result['failed'] is False

    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.load_yaml_files')
    @patch('plugins.action.common.nac_dc_validate.data_model_key_check')
    def test_unsupported_fabric_type_error(self, mock_key_check, mock_load_yaml, mock_listdir, mock_exists, mock_parent_run):
        """Test error handling for unsupported fabric type."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        # Mock data model with unsupported fabric type
        mock_data = {
            'vxlan': {
                'fabric': {
                    'type': 'UNSUPPORTED_TYPE'
                }
            }
        }
        mock_load_yaml.return_value = mock_data
        mock_key_check.return_value = {
            'keys_found': ['fabric'],
            'keys_data': ['fabric']
        }
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules/',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/path/to/rules'
        }
        
        action_module = self.create_action_module(task_args)
        result = action_module.run(task_vars=task_vars)
        
        # Should fail with unsupported fabric type error
        assert result['failed'] is True
        assert 'is not a supported fabric type' in result['msg']

    @patch('plugins.action.common.nac_dc_validate.IAC_VALIDATE_IMPORT_ERROR', None)
    @patch('ansible.plugins.action.ActionBase.run')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('plugins.action.common.nac_dc_validate.load_yaml_files')
    @patch('plugins.action.common.nac_dc_validate.data_model_key_check')
    def test_missing_fabric_type_error(self, mock_key_check, mock_load_yaml, mock_listdir, mock_exists, mock_parent_run):
        """Test error handling when fabric type is missing."""
        mock_parent_run.return_value = {}
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.yaml']
        
        # Mock data model with fabric section but no type
        mock_data = {
            'vxlan': {
                'fabric': {
                    'name': 'test-fabric'
                }
            }
        }
        mock_load_yaml.return_value = mock_data
        mock_key_check.return_value = {
            'keys_found': ['fabric'],
            'keys_data': ['fabric']
        }
        
        task_args = {
            'schema': '/path/to/schema.yaml',
            'rules': '/path/to/rules/',
            'mdata': '/path/to/data'
        }
        
        task_vars = {
            'role_path': '/path/to/rules'
        }
        
        action_module = self.create_action_module(task_args)
        result = action_module.run(task_vars=task_vars)
        
        # Should fail with missing fabric type error
        assert result['failed'] is True
        assert 'is not defined in the data model' in result['msg']

    def test_import_success_path(self):
        """Test the successful import path (lines 35-36)."""
        # This test is to ensure the import success path is covered
        # The else clause sets IAC_VALIDATE_IMPORT_ERROR = None on successful import
        # This should already be covered by other tests, but let's be explicit
        import sys
        import importlib
        
        # Temporarily remove the module to force reimport
        module_path = 'plugins.action.common.nac_dc_validate'
        if module_path in sys.modules:
            del sys.modules[module_path]
        
        # Mock successful import
        with patch('plugins.action.common.nac_dc_validate.load_yaml_files'):
            with patch('plugins.action.common.nac_dc_validate.iac_validate.validator'):
                with patch('plugins.action.common.nac_dc_validate.DEFAULT_SCHEMA', '/default/schema.yaml'):
                    # Import the module - should set IAC_VALIDATE_IMPORT_ERROR = None
                    from plugins.action.common.nac_dc_validate import IAC_VALIDATE_IMPORT_ERROR
                    
                    # Should be None on successful import
                    assert IAC_VALIDATE_IMPORT_ERROR is None

# Copyright (c) 2025 Cisco Systems, Inc. and its affiliates
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# SPDX-License-Identifier: MIT

"""
Unit tests for check_roles action plugin.
"""

from unittest.mock import MagicMock, patch

# Try to import from the plugins directory
try:
    from plugins.action.common.check_roles import ActionModule as CheckRolesActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.common.check_roles import ActionModule as CheckRolesActionModule


class TestCheckRolesActionModule:
    """Test the check_roles action module."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mock task
        self.mock_task = MagicMock()
        self.mock_task.action = "check_roles"
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
            action_module = CheckRolesActionModule(
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
            'role_list': ['cisco.nac_dc_vxlan.create', 'cisco.nac_dc_vxlan.deploy']
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert isinstance(result, dict)

    def test_run_with_empty_args(self):
        """Test run method with empty arguments."""
        task_args = {
            'role_list': []
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert isinstance(result, dict)
            assert result['save_previous'] is False

    def test_run_with_none_task_vars(self):
        """Test run method with None task_vars."""
        task_args = {
            'role_list': ['cisco.nac_dc_vxlan.create']
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run(task_vars=None)
            assert isinstance(result, dict)
            assert result['save_previous'] is True

    def test_run_with_empty_task_vars(self):
        """Test run method with empty task_vars."""
        task_args = {
            'role_list': ['cisco.nac_dc_vxlan.deploy']
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run(task_vars={})
            assert isinstance(result, dict)
            assert result['save_previous'] is True

    @patch('ansible.plugins.action.ActionBase.run')
    def test_parent_run_called(self, mock_parent_run):
        """Test that parent run method is called."""
        mock_parent_run.return_value = {}
        task_args = {
            'role_list': ['cisco.nac_dc_vxlan.remove']
        }
        action_module = self.create_action_module(task_args)

        action_module.run()

        mock_parent_run.assert_called_once()

    def test_run_with_typical_task_vars(self):
        """Test run method with typical task_vars structure."""
        task_args = {
            'role_list': ['other.role', 'cisco.nac_dc_vxlan.create', 'another.role']
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
            assert result['save_previous'] is True

    def test_run_does_not_set_failed_by_default(self):
        """Test that run method doesn't set failed=True by default."""
        task_args = {
            'role_list': ['other.role.not.matching']
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert result.get('failed', False) is False
            assert result['save_previous'] is False

    def test_inheritance_from_action_base(self):
        """Test that the action module inherits from ActionBase."""
        action_module = self.create_action_module()

        from ansible.plugins.action import ActionBase
        assert isinstance(action_module, ActionBase)

    def test_save_previous_false_for_no_matching_roles(self):
        """Test that save_previous is False when no matching roles are found."""
        task_args = {
            'role_list': ['other.role', 'another.role', 'third.role']
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert result['save_previous'] is False

    def test_save_previous_true_for_create_role(self):
        """Test that save_previous is True for create role."""
        task_args = {
            'role_list': ['other.role', 'cisco.nac_dc_vxlan.create']
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert result['save_previous'] is True

    def test_save_previous_true_for_deploy_role(self):
        """Test that save_previous is True for deploy role."""
        task_args = {
            'role_list': ['cisco.nac_dc_vxlan.deploy', 'other.role']
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert result['save_previous'] is True

    def test_save_previous_true_for_remove_role(self):
        """Test that save_previous is True for remove role."""
        task_args = {
            'role_list': ['cisco.nac_dc_vxlan.remove']
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert result['save_previous'] is True

    def test_save_previous_true_for_multiple_matching_roles(self):
        """Test that save_previous is True when multiple matching roles are present."""
        task_args = {
            'role_list': [
                'cisco.nac_dc_vxlan.create',
                'cisco.nac_dc_vxlan.deploy',
                'cisco.nac_dc_vxlan.remove'
            ]
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert result['save_previous'] is True

    def test_partial_role_name_matching(self):
        """Test that partial role name matching doesn't trigger save_previous."""
        task_args = {
            'role_list': [
                'cisco.nac_dc_vxlan.create_extra',
                'cisco.nac_dc_vxlan.deploy_more',
                'cisco.nac_dc_vxlan.remove_old'
            ]
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert result['save_previous'] is False

    def test_case_sensitive_role_matching(self):
        """Test that role matching is case sensitive."""
        task_args = {
            'role_list': [
                'CISCO.NAC_DC_VXLAN.CREATE',
                'cisco.nac_dc_vxlan.DEPLOY',
                'Cisco.Nac_Dc_Vxlan.Remove'
            ]
        }
        action_module = self.create_action_module(task_args)

        with patch('ansible.plugins.action.ActionBase.run', return_value={}):
            result = action_module.run()
            assert result['save_previous'] is False

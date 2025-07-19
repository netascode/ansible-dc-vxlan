"""
Unit tests for fabrics_deploy action plugin.
"""
import unittest
from unittest.mock import patch

# Try to import from the plugins directory
try:
    from plugins.action.dtc.fabrics_deploy import ActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.dtc.fabrics_deploy import ActionModule
from .base_test import ActionModuleTestCase


class TestFabricsDeployActionModule(ActionModuleTestCase):
    """Test cases for fabrics_deploy action plugin."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

    def test_run_single_fabric_success(self):
        """Test run with single fabric deployment success."""
        fabrics = ["fabric1"]

        mock_response = {
            'response': {
                'RETURN_CODE': 200,
                'METHOD': 'POST',
                'MESSAGE': 'OK',
                'DATA': {
                    'status': 'Configuration deployment completed.'
                }
            }
        }

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run and display
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run, \
             patch('plugins.action.dtc.fabrics_deploy.display') as mock_display:

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])

            # Verify display message was called
            mock_display.display.assert_called_once_with("Executing config-deploy on Fabric: fabric1")

            # Verify the correct API call was made
            mock_execute.assert_called_once_with(
                module_name="cisco.dcnm.dcnm_rest",
                module_args={
                    "method": "POST",
                    "path": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/fabric1/config-deploy?forceShowRun=false",
                },
                task_vars=None,
                tmp=None
            )

    def test_run_single_fabric_failure(self):
        """Test run with single fabric deployment failure."""
        fabrics = ["fabric1"]

        mock_response = {
            'msg': {
                'RETURN_CODE': 400,
                'METHOD': 'POST',
                'MESSAGE': 'Bad Request',
                'DATA': {
                    'message': 'Deployment failed due to configuration errors'
                }
            }
        }

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run, \
             patch('plugins.action.dtc.fabrics_deploy.display'):

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertTrue(result['failed'])
            self.assertIn('For fabric fabric1', result['msg'])

    def test_run_multiple_fabrics_success(self):
        """Test run with multiple fabric deployments success."""
        fabrics = ["fabric1", "fabric2"]

        mock_response = {
            'response': {
                'RETURN_CODE': 200,
                'METHOD': 'POST',
                'MESSAGE': 'OK',
                'DATA': {
                    'status': 'Configuration deployment completed.'
                }
            }
        }

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run, \
             patch('plugins.action.dtc.fabrics_deploy.display') as mock_display:

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])

            # Verify display messages were called for both fabrics
            expected_calls = [
                unittest.mock.call("Executing config-deploy on Fabric: fabric1"),
                unittest.mock.call("Executing config-deploy on Fabric: fabric2")
            ]
            mock_display.display.assert_has_calls(expected_calls)

            # Verify the correct API calls were made
            self.assertEqual(mock_execute.call_count, 2)

    def test_run_multiple_fabrics_continue_on_failure(self):
        """Test run with multiple fabrics, continuing on failure."""
        fabrics = ["fabric1", "fabric2"]

        mock_response = {
            'msg': {
                'RETURN_CODE': 400,
                'METHOD': 'POST',
                'MESSAGE': 'Bad Request',
                'DATA': {
                    'message': 'Deployment failed'
                }
            }
        }

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run, \
             patch('plugins.action.dtc.fabrics_deploy.display'):

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertTrue(result['failed'])

            # Should be called for both fabrics since it continues on failure
            self.assertEqual(mock_execute.call_count, 2)

    def test_run_mixed_success_failure(self):
        """Test run with mixed success and failure responses."""
        fabrics = ["fabric1", "fabric2"]

        success_response = {
            'response': {
                'RETURN_CODE': 200,
                'METHOD': 'POST',
                'MESSAGE': 'OK',
                'DATA': {
                    'status': 'Configuration deployment completed.'
                }
            }
        }

        failure_response = {
            'msg': {
                'RETURN_CODE': 400,
                'METHOD': 'POST',
                'MESSAGE': 'Bad Request',
                'DATA': {
                    'message': 'Deployment failed'
                }
            }
        }

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run, \
             patch('plugins.action.dtc.fabrics_deploy.display'):

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.side_effect = [success_response, failure_response]

            result = action_module.run()

            self.assertTrue(result['changed'])  # First succeeded
            self.assertTrue(result['failed'])   # Second failed

            # Should be called twice
            self.assertEqual(mock_execute.call_count, 2)

    def test_run_no_response_key(self):
        """Test run when response key is missing."""
        fabrics = ["fabric1"]

        mock_response = {}  # No response or msg key

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run, \
             patch('plugins.action.dtc.fabrics_deploy.display'):

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertFalse(result['failed'])

    def test_run_non_200_response_code(self):
        """Test run with non-200 response code in success response."""
        fabrics = ["fabric1"]

        mock_response = {
            'response': {
                'RETURN_CODE': 404,
                'METHOD': 'POST',
                'MESSAGE': 'Not Found',
                'DATA': {
                    'status': 'Fabric not found.'
                }
            }
        }

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run, \
             patch('plugins.action.dtc.fabrics_deploy.display'):

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertFalse(result['failed'])

    def test_run_msg_with_200_return_code(self):
        """Test run when msg key exists but with 200 return code."""
        fabrics = ["fabric1"]

        mock_response = {
            'msg': {
                'RETURN_CODE': 200,
                'METHOD': 'POST',
                'MESSAGE': 'OK',
                'DATA': {
                    'message': 'Success message'
                }
            }
        }

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run, \
             patch('plugins.action.dtc.fabrics_deploy.display'):

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertFalse(result['failed'])

    def test_run_empty_fabrics_list(self):
        """Test run with empty fabrics list."""
        fabrics = []

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run, \
             patch('plugins.action.dtc.fabrics_deploy.display'):

            mock_parent_run.return_value = {'changed': False, 'failed': False}

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertFalse(result['failed'])

            # No execute_module calls should be made
            mock_execute.assert_not_called()

    def test_run_display_messages(self):
        """Test that display messages are shown for each fabric."""
        fabrics = ["fabric1", "fabric2"]

        mock_response = {
            'response': {
                'RETURN_CODE': 200,
                'METHOD': 'POST',
                'MESSAGE': 'OK',
                'DATA': {
                    'status': 'Configuration deployment completed.'
                }
            }
        }

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module method and ActionBase.run
        with patch.object(action_module, '_execute_module') as mock_execute, \
             patch('ansible.plugins.action.ActionBase.run') as mock_parent_run, \
             patch('plugins.action.dtc.fabrics_deploy.display') as mock_display:

            mock_parent_run.return_value = {'changed': False, 'failed': False}
            mock_execute.return_value = mock_response

            action_module.run()

            # Verify all display messages
            expected_calls = [
                unittest.mock.call("Executing config-deploy on Fabric: fabric1"),
                unittest.mock.call("Executing config-deploy on Fabric: fabric2")
            ]
            mock_display.display.assert_has_calls(expected_calls)


if __name__ == '__main__':
    unittest.main()

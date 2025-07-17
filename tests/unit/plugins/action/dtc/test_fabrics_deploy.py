"""
Unit tests for fabrics_deploy action plugin.
"""
import unittest
from unittest.mock import MagicMock, patch

from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.fabrics_deploy import ActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.base_test import ActionModuleTestCase


class TestFabricsDeployActionModule(ActionModuleTestCase):
    """Test cases for fabrics_deploy action plugin."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.action_module = self.create_action_module(ActionModule)

    def test_run_single_fabric_success(self):
        """Test run with single fabric successful deployment."""
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
        
        # Mock the run method from parent class and _execute_module
        with patch.object(ActionModule, 'run') as mock_parent_run, \
             patch.object(ActionModule, '_execute_module') as mock_execute:
            
            mock_parent_run.return_value = {'changed': False}
            mock_execute.return_value = mock_response
            
            result = action_module.run()
            
            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])
            
            # Verify the correct API call was made
            mock_execute.assert_called_once_with(
                module_name="cisco.dcnm.dcnm_rest",
                module_args={
                    "method": "POST",
                    "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/{fabrics[0]}/config-deploy?forceShowRun=false",
                },
                task_vars=None,
                tmp=None
            )

    def test_run_multiple_fabrics_success(self):
        """Test run with multiple fabrics successful deployment."""
        fabrics = ["fabric1", "fabric2", "fabric3"]
        
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
        
        # Mock the run method from parent class and _execute_module
        with patch.object(ActionModule, 'run') as mock_parent_run, \
             patch.object(ActionModule, '_execute_module') as mock_execute:
            
            mock_parent_run.return_value = {'changed': False}
            mock_execute.return_value = mock_response
            
            result = action_module.run()
            
            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])
            
            # Verify the correct number of API calls were made
            self.assertEqual(mock_execute.call_count, len(fabrics))

    def test_run_single_fabric_failure(self):
        """Test run with single fabric failed deployment."""
        fabrics = ["fabric1"]
        
        mock_response = {
            'msg': {
                'RETURN_CODE': 400,
                'METHOD': 'POST',
                'MESSAGE': 'Bad Request',
                'DATA': {
                    'path': 'rest/control/fabrics/fabric1/config-deploy?forceShowRun=false',
                    'Error': 'Bad Request Error',
                    'message': 'Deployment failed due to configuration error',
                    'timestamp': '2025-02-24 13:49:41.024',
                    'status': '400'
                }
            }
        }
        
        task_args = {
            'fabrics': fabrics
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        # Mock the run method from parent class and _execute_module
        with patch.object(ActionModule, 'run') as mock_parent_run, \
             patch.object(ActionModule, '_execute_module') as mock_execute:
            
            mock_parent_run.return_value = {'changed': False}
            mock_execute.return_value = mock_response
            
            result = action_module.run()
            
            self.assertFalse(result['changed'])
            self.assertTrue(result['failed'])
            self.assertIn('For fabric fabric1', result['msg'])
            self.assertIn('Deployment failed due to configuration error', result['msg'])

    def test_run_mixed_success_failure(self):
        """Test run with mixed success and failure scenarios."""
        fabrics = ["fabric1", "fabric2"]
        
        mock_success_response = {
            'response': {
                'RETURN_CODE': 200,
                'METHOD': 'POST',
                'MESSAGE': 'OK',
                'DATA': {
                    'status': 'Configuration deployment completed.'
                }
            }
        }
        
        mock_failure_response = {
            'msg': {
                'RETURN_CODE': 400,
                'METHOD': 'POST',
                'MESSAGE': 'Bad Request',
                'DATA': {
                    'path': 'rest/control/fabrics/fabric2/config-deploy?forceShowRun=false',
                    'Error': 'Bad Request Error',
                    'message': 'Deployment failed',
                    'timestamp': '2025-02-24 13:49:41.024',
                    'status': '400'
                }
            }
        }
        
        task_args = {
            'fabrics': fabrics
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        # Mock the run method from parent class and _execute_module
        with patch.object(ActionModule, 'run') as mock_parent_run, \
             patch.object(ActionModule, '_execute_module') as mock_execute:
            
            mock_parent_run.return_value = {'changed': False}
            mock_execute.side_effect = [mock_success_response, mock_failure_response]
            
            result = action_module.run()
            
            self.assertTrue(result['changed'])  # First fabric succeeded
            self.assertTrue(result['failed'])   # Second fabric failed
            self.assertIn('For fabric fabric2', result['msg'])

    def test_run_no_response_key(self):
        """Test run when response key is missing."""
        fabrics = ["fabric1"]
        
        mock_response = {
            'other_key': 'value'
        }
        
        task_args = {
            'fabrics': fabrics
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        # Mock the run method from parent class and _execute_module
        with patch.object(ActionModule, 'run') as mock_parent_run, \
             patch.object(ActionModule, '_execute_module') as mock_execute:
            
            mock_parent_run.return_value = {'changed': False}
            mock_execute.return_value = mock_response
            
            result = action_module.run()
            
            self.assertFalse(result['changed'])
            self.assertFalse(result['failed'])

    def test_run_non_200_response_code(self):
        """Test run with non-200 response code in success response."""
        fabrics = ["fabric1"]
        
        mock_response = {
            'response': {
                'RETURN_CODE': 201,
                'METHOD': 'POST',
                'MESSAGE': 'Created',
                'DATA': {
                    'status': 'Configuration deployment completed.'
                }
            }
        }
        
        task_args = {
            'fabrics': fabrics
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        # Mock the run method from parent class and _execute_module
        with patch.object(ActionModule, 'run') as mock_parent_run, \
             patch.object(ActionModule, '_execute_module') as mock_execute:
            
            mock_parent_run.return_value = {'changed': False}
            mock_execute.return_value = mock_response
            
            result = action_module.run()
            
            self.assertFalse(result['changed'])  # Only 200 sets changed=True
            self.assertFalse(result['failed'])

    def test_run_empty_fabrics_list(self):
        """Test run with empty fabrics list."""
        fabrics = []
        
        task_args = {
            'fabrics': fabrics
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        # Mock the run method from parent class and _execute_module
        with patch.object(ActionModule, 'run') as mock_parent_run, \
             patch.object(ActionModule, '_execute_module') as mock_execute:
            
            mock_parent_run.return_value = {'changed': False}
            
            result = action_module.run()
            
            self.assertFalse(result['changed'])
            self.assertFalse(result['failed'])
            mock_execute.assert_not_called()

    def test_run_msg_with_200_return_code(self):
        """Test run when msg key exists but return code is 200."""
        fabrics = ["fabric1"]
        
        mock_response = {
            'msg': {
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
        
        # Mock the run method from parent class and _execute_module
        with patch.object(ActionModule, 'run') as mock_parent_run, \
             patch.object(ActionModule, '_execute_module') as mock_execute:
            
            mock_parent_run.return_value = {'changed': False}
            mock_execute.return_value = mock_response
            
            result = action_module.run()
            
            self.assertFalse(result['changed'])
            self.assertFalse(result['failed'])

    def test_run_multiple_fabrics_stop_on_first_failure(self):
        """Test run with multiple fabrics where first fails."""
        fabrics = ["fabric1", "fabric2", "fabric3"]
        
        mock_failure_response = {
            'msg': {
                'RETURN_CODE': 400,
                'METHOD': 'POST',
                'MESSAGE': 'Bad Request',
                'DATA': {
                    'path': 'rest/control/fabrics/fabric1/config-deploy?forceShowRun=false',
                    'Error': 'Bad Request Error',
                    'message': 'First fabric failed',
                    'timestamp': '2025-02-24 13:49:41.024',
                    'status': '400'
                }
            }
        }
        
        task_args = {
            'fabrics': fabrics
        }
        
        action_module = self.create_action_module(ActionModule, task_args)
        
        # Mock the run method from parent class and _execute_module
        with patch.object(ActionModule, 'run') as mock_parent_run, \
             patch.object(ActionModule, '_execute_module') as mock_execute:
            
            mock_parent_run.return_value = {'changed': False}
            mock_execute.return_value = mock_failure_response
            
            result = action_module.run()
            
            self.assertFalse(result['changed'])
            self.assertTrue(result['failed'])
            self.assertIn('For fabric fabric1', result['msg'])
            # Should still process all fabrics, not stop on first failure
            self.assertEqual(mock_execute.call_count, len(fabrics))

    @patch('ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.fabrics_deploy.display')
    def test_run_display_messages(self, mock_display):
        """Test run displays correct messages."""
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
        
        # Mock the run method from parent class and _execute_module
        with patch.object(ActionModule, 'run') as mock_parent_run, \
             patch.object(ActionModule, '_execute_module') as mock_execute:
            
            mock_parent_run.return_value = {'changed': False}
            mock_execute.return_value = mock_response
            
            result = action_module.run()
            
            # Verify display messages were called for each fabric
            expected_calls = [
                'Executing config-deploy on Fabric: fabric1',
                'Executing config-deploy on Fabric: fabric2'
            ]
            
            actual_calls = [call[0][0] for call in mock_display.display.call_args_list]
            self.assertEqual(actual_calls, expected_calls)


if __name__ == '__main__':
    unittest.main()

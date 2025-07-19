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
Unit tests for fabrics_config_save action plugin.
"""

from unittest.mock import patch

# Try to import from the plugins directory
try:
    from plugins.action.dtc.fabrics_config_save import ActionModule
except ImportError:
    # Fallback for when running tests from different locations
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    from plugins.action.dtc.fabrics_config_save import ActionModule
from .base_test import ActionModuleTestCase


class TestFabricsConfigSaveActionModule(ActionModuleTestCase):
    """Test cases for fabrics_config_save action plugin."""

    def test_run_single_fabric_success(self):
        """Test run with single fabric successful config save."""
        fabrics = ["fabric1"]

        mock_response = {
            'response': {
                'RETURN_CODE': 200,
                'METHOD': 'POST',
                'MESSAGE': 'OK',
                'DATA': {
                    'status': 'Config save is completed'
                }
            }
        }

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])

    def test_run_single_fabric_failure(self):
        """Test run with single fabric failed config save."""
        fabrics = ["fabric1"]

        mock_response = {
            'msg': {
                'RETURN_CODE': 400,
                'METHOD': 'POST',
                'MESSAGE': 'Bad Request',
                'DATA': {
                    'path': 'rest/control/fabrics/fabric1/config-save',
                    'Error': 'Bad Request Error',
                    'message': 'Config save failed due to error',
                    'timestamp': '2025-02-24 13:49:41.024',
                    'status': '400'
                }
            }
        }

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertTrue(result['failed'])
            self.assertIn('fabric1', result['msg'])

    def test_run_multiple_fabrics_success(self):
        """Test run with multiple fabrics successful config save."""
        fabrics = ["fabric1", "fabric2", "fabric3"]

        mock_response = {
            'response': {
                'RETURN_CODE': 200,
                'METHOD': 'POST',
                'MESSAGE': 'OK',
                'DATA': {
                    'status': 'Config save is completed'
                }
            }
        }

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertTrue(result['changed'])
            self.assertFalse(result['failed'])

    def test_run_empty_fabrics_list(self):
        """Test run with empty fabrics list."""
        fabrics = []

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        result = action_module.run()

        self.assertFalse(result['changed'])
        self.assertFalse(result['failed'])

    def test_run_mixed_success_failure(self):
        """Test run with mixed success and failure scenarios."""
        fabrics = ["fabric1", "fabric2"]

        mock_success_response = {
            'response': {
                'RETURN_CODE': 200,
                'METHOD': 'POST',
                'MESSAGE': 'OK',
                'DATA': {
                    'status': 'Config save is completed'
                }
            }
        }

        mock_failure_response = {
            'msg': {
                'RETURN_CODE': 400,
                'METHOD': 'POST',
                'MESSAGE': 'Bad Request',
                'DATA': {
                    'path': 'rest/control/fabrics/fabric2/config-save',
                    'Error': 'Bad Request Error',
                    'message': 'Config save failed',
                    'timestamp': '2025-02-24 13:49:41.024',
                    'status': '400'
                }
            }
        }

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock _execute_module to return different responses
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.side_effect = [mock_success_response, mock_failure_response]

            result = action_module.run()

            self.assertTrue(result['changed'])  # First fabric succeeded
            self.assertTrue(result['failed'])   # Second fabric failed

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

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
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
                    'status': 'Config save is completed'
                }
            }
        }

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertFalse(result['changed'])  # Only 200 sets changed=True
            self.assertFalse(result['failed'])

    def test_run_msg_with_200_return_code(self):
        """Test run when msg key exists but return code is 200."""
        fabrics = ["fabric1"]

        mock_response = {
            'msg': {
                'RETURN_CODE': 200,
                'METHOD': 'POST',
                'MESSAGE': 'OK',
                'DATA': {
                    'status': 'Config save is completed'
                }
            }
        }

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_response

            result = action_module.run()

            self.assertFalse(result['changed'])
            self.assertFalse(result['failed'])

    @patch('plugins.action.dtc.fabrics_config_save.display')
    def test_run_display_messages(self, mock_display):
        """Test run displays correct messages."""
        fabrics = ["fabric1", "fabric2"]

        mock_response = {
            'response': {
                'RETURN_CODE': 200,
                'METHOD': 'POST',
                'MESSAGE': 'OK',
                'DATA': {
                    'status': 'Config save is completed'
                }
            }
        }

        task_args = {
            'fabrics': fabrics
        }

        action_module = self.create_action_module(ActionModule, task_args)

        # Mock only _execute_module
        with patch.object(ActionModule, '_execute_module') as mock_execute:
            mock_execute.return_value = mock_response

            result = action_module.run()

            # Verify display messages were called for each fabric
            expected_calls = [
                'Executing config-save on Fabric: fabric1',
                'Executing config-save on Fabric: fabric2'
            ]

            actual_calls = [call[0][0] for call in mock_display.display.call_args_list]
            self.assertEqual(actual_calls, expected_calls)

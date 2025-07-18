"""
Base test class for DTC action plugins.
"""
import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import tempfile
import shutil

from ansible.playbook.task import Task
from ansible.template import Templar
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.executor.task_executor import TaskExecutor


class ActionModuleTestCase(unittest.TestCase):
    """Base test case for action module tests."""

    def setUp(self):
        """Set up test fixtures."""
        self.loader = DataLoader()
        self.inventory = InventoryManager(loader=self.loader, sources=[])
        self.variable_manager = VariableManager(loader=self.loader, inventory=self.inventory)
        
        # Create mock task
        self.task = Task()
        self.task.args = {}
        self.task.action = 'test_action'
        
        # Create mock connection
        self.connection = MagicMock()
        
        # Create mock play context
        self.play_context = MagicMock()
        
        # Create mock loader
        self.loader_mock = MagicMock()
        
        # Create mock templar
        self.templar = Templar(loader=self.loader, variables={})
        
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_temp_file(self, content, filename=None):
        """Create a temporary file with given content."""
        if filename is None:
            fd, filepath = tempfile.mkstemp(dir=self.temp_dir, text=True)
            with os.fdopen(fd, 'w') as f:
                f.write(content)
        else:
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write(content)
        return filepath
    
    def create_action_module(self, action_class, task_args=None):
        """Create an action module instance for testing."""
        if task_args:
            self.task.args = task_args
        
        action_module = action_class(
            task=self.task,
            connection=self.connection,
            play_context=self.play_context,
            loader=self.loader_mock,
            templar=self.templar,
            shared_loader_obj=None
        )
        
        return action_module

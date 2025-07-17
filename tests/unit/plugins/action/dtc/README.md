# DTC Action Plugin Unit Tests

This directory contains comprehensive unit tests for the DTC (Direct-to-Controller) action plugins in the cisco.nac_dc_vxlan collection.

## Test Coverage

The test suite covers the following action plugins:

### Core Plugins
1. **diff_model_changes** - Tests file comparison and MD5 hashing logic
2. **add_device_check** - Tests device validation and configuration checks
3. **verify_tags** - Tests tag validation and filtering
4. **vpc_pair_check** - Tests VPC pair configuration validation
5. **get_poap_data** - Tests POAP (Power-On Auto Provisioning) data retrieval
6. **existing_links_check** - Tests link comparison and template matching
7. **fabric_check_sync** - Tests fabric synchronization status checking
8. **fabrics_deploy** - Tests fabric deployment operations

### Test Structure

Each test file follows a consistent pattern:
- `test_<plugin_name>.py` - Main test file for the plugin
- `TestXxxActionModule` - Test class for the action module
- Comprehensive test methods covering:
  - Success scenarios
  - Error conditions
  - Edge cases
  - Input validation
  - API interactions (mocked)

### Base Test Class

The `base_test.py` file provides:
- `ActionModuleTestCase` - Base class for all action plugin tests
- Common setup and teardown methods
- Helper methods for creating test fixtures
- Mock objects for Ansible components

## Running Tests

### Using unittest (built-in)

```bash
# Run all tests
python -m unittest discover -s tests/unit/plugins/action/dtc -p "test_*.py" -v

# Run specific test file
python -m unittest tests.unit.plugins.action.dtc.test_diff_model_changes -v

# Run specific test class
python -m unittest tests.unit.plugins.action.dtc.test_diff_model_changes.TestDiffModelChangesActionModule -v

# Run specific test method
python -m unittest tests.unit.plugins.action.dtc.test_diff_model_changes.TestDiffModelChangesActionModule.test_run_identical_files -v
```

### Using pytest (recommended)

```bash
# Install pytest if not already installed
pip install pytest

# Run all tests from the collections directory
cd collections
PYTHONPATH=/path/to/collections python -m pytest ansible_collections/cisco/nac_dc_vxlan/tests/unit/plugins/action/dtc/ -v

# Run with coverage
pip install pytest-cov
PYTHONPATH=/path/to/collections python -m pytest ansible_collections/cisco/nac_dc_vxlan/tests/unit/plugins/action/dtc/ --cov=ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc --cov-report=term-missing

# Run specific test file
PYTHONPATH=/path/to/collections python -m pytest ansible_collections/cisco/nac_dc_vxlan/tests/unit/plugins/action/dtc/test_diff_model_changes.py -v

# Run quietly (minimal output)
PYTHONPATH=/path/to/collections python -m pytest ansible_collections/cisco/nac_dc_vxlan/tests/unit/plugins/action/dtc/ -q
```

## Test Categories

### Unit Tests
- Test individual functions and methods
- Mock external dependencies
- Fast execution
- High code coverage

### Integration Tests
- Test plugin interactions with Ansible framework
- Test API interactions (where applicable)
- Slower execution
- End-to-end functionality

## Test Data and Fixtures

Tests use a variety of test data:
- Mock fabric configurations
- Sample device data
- Test file contents
- API response examples

## Mocking Strategy

The tests use extensive mocking to:
- Isolate units under test
- Avoid external dependencies
- Control test conditions
- Ensure predictable results

Common mocked components:
- Ansible ActionBase methods
- File system operations
- Network API calls
- Module execution

## Coverage Goals

The test suite aims for:
- **Line Coverage**: >95%
- **Branch Coverage**: >90%
- **Function Coverage**: 100%

## Test Maintenance

### Adding New Tests

When adding new action plugins:

1. Create a new test file: `test_<plugin_name>.py`
2. Inherit from `ActionModuleTestCase`
3. Follow the existing test patterns
4. Add comprehensive test methods
5. Update the test runner to include new tests

### Test Naming Convention

- Test files: `test_<plugin_name>.py`
- Test classes: `Test<PluginName>ActionModule`
- Test methods: `test_<scenario_description>`

### Common Test Patterns

```python
def test_run_success_scenario(self):
    \"\"\"Test successful execution.\"\"\"
    # Arrange
    task_args = {'param': 'value'}
    expected_result = {'changed': True}
    
    # Act
    action_module = self.create_action_module(ActionModule, task_args)
    result = action_module.run()
    
    # Assert
    self.assertEqual(result, expected_result)

def test_run_failure_scenario(self):
    \"\"\"Test failure handling.\"\"\"
    # Test error conditions
    pass

def test_run_edge_case(self):
    \"\"\"Test edge cases.\"\"\"
    # Test boundary conditions
    pass
```

## Dependencies

The tests require:
- Python 3.6+
- unittest (built-in)
- mock (built-in from Python 3.3+)
- ansible-core
- Optional: pytest, pytest-cov for enhanced testing

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the collection path is in sys.path
2. **Mock Issues**: Verify mock patch targets are correct
3. **Test Isolation**: Ensure tests don't interfere with each other
4. **File Permissions**: Check temporary file creation permissions

### Debug Mode

Run tests with increased verbosity:

```bash
python -m unittest tests.unit.plugins.action.dtc.test_diff_model_changes -v
```

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

When contributing new tests:

1. Follow the existing patterns
2. Ensure comprehensive coverage
3. Add docstrings to test methods
4. Test both success and failure scenarios
5. Include edge cases
6. Update this README if needed

## Future Enhancements

Potential improvements:
- Add property-based testing
- Implement test fixtures for common scenarios
- Add performance benchmarks
- Integrate with CI/CD pipeline
- Add mutation testing

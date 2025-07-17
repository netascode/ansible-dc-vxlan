# Makefile for DTC Action Plugin Tests
# 
# This Makefile provides convenient targets for running unit tests
# for the DTC action plugins in the cisco.nac_dc_vxlan collection.

# Variables
PYTHON := python3
TEST_DIR := tests/unit/plugins/action/dtc
VENV_DIR := venv
REQUIREMENTS := requirements-test.txt

# Default target
.PHONY: help
help:
	@echo "DTC Action Plugin Test Suite"
	@echo "============================"
	@echo ""
	@echo "Available targets:"
	@echo "  help                 Show this help message"
	@echo "  test                 Run all tests"
	@echo "  test-verbose         Run all tests with verbose output"
	@echo "  test-plugin          Run tests for specific plugin (usage: make test-plugin PLUGIN=diff_model_changes)"
	@echo "  test-coverage        Run tests with coverage report"
	@echo "  test-html-coverage   Run tests with HTML coverage report"
	@echo "  test-watch           Run tests in watch mode (requires pytest-watch)"
	@echo "  clean                Clean up test artifacts"
	@echo "  setup-venv           Set up virtual environment"
	@echo "  install-deps         Install test dependencies"
	@echo "  lint                 Run linting checks"
	@echo "  format               Format code with black"
	@echo ""
	@echo "Available plugins for test-plugin:"
	@echo "  diff_model_changes, add_device_check, verify_tags, vpc_pair_check,"
	@echo "  get_poap_data, existing_links_check, fabric_check_sync, fabrics_deploy"

# Test targets
.PHONY: test
test:
	@echo "Running all DTC action plugin tests..."
	cd $(TEST_DIR) && $(PYTHON) test_all.py

.PHONY: test-verbose
test-verbose:
	@echo "Running all DTC action plugin tests with verbose output..."
	cd $(TEST_DIR) && $(PYTHON) -m unittest discover -s . -p "test_*.py" -v

.PHONY: test-plugin
test-plugin:
	@if [ -z "$(PLUGIN)" ]; then \
		echo "Error: PLUGIN variable not set. Usage: make test-plugin PLUGIN=diff_model_changes"; \
		exit 1; \
	fi
	@echo "Running tests for plugin: $(PLUGIN)"
	cd $(TEST_DIR) && $(PYTHON) test_all.py $(PLUGIN)

.PHONY: test-coverage
test-coverage:
	@echo "Running tests with coverage..."
	cd $(TEST_DIR) && $(PYTHON) -m pytest --cov=../../../../../plugins/action/dtc --cov-report=term-missing .

.PHONY: test-html-coverage
test-html-coverage:
	@echo "Running tests with HTML coverage report..."
	cd $(TEST_DIR) && $(PYTHON) -m pytest --cov=../../../../../plugins/action/dtc --cov-report=html .
	@echo "HTML coverage report generated in htmlcov/"

.PHONY: test-watch
test-watch:
	@echo "Running tests in watch mode..."
	cd $(TEST_DIR) && $(PYTHON) -m ptw .

# Individual test file targets
.PHONY: test-diff-model-changes
test-diff-model-changes:
	cd $(TEST_DIR) && $(PYTHON) -m unittest test_diff_model_changes -v

.PHONY: test-add-device-check
test-add-device-check:
	cd $(TEST_DIR) && $(PYTHON) -m unittest test_add_device_check -v

.PHONY: test-verify-tags
test-verify-tags:
	cd $(TEST_DIR) && $(PYTHON) -m unittest test_verify_tags -v

.PHONY: test-vpc-pair-check
test-vpc-pair-check:
	cd $(TEST_DIR) && $(PYTHON) -m unittest test_vpc_pair_check -v

.PHONY: test-get-poap-data
test-get-poap-data:
	cd $(TEST_DIR) && $(PYTHON) -m unittest test_get_poap_data -v

.PHONY: test-existing-links-check
test-existing-links-check:
	cd $(TEST_DIR) && $(PYTHON) -m unittest test_existing_links_check -v

.PHONY: test-fabric-check-sync
test-fabric-check-sync:
	cd $(TEST_DIR) && $(PYTHON) -m unittest test_fabric_check_sync -v

.PHONY: test-fabrics-deploy
test-fabrics-deploy:
	cd $(TEST_DIR) && $(PYTHON) -m unittest test_fabrics_deploy -v

# Setup and dependency targets
.PHONY: setup-venv
setup-venv:
	@echo "Setting up virtual environment..."
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "Virtual environment created. Activate with: source $(VENV_DIR)/bin/activate"

.PHONY: install-deps
install-deps:
	@echo "Installing test dependencies..."
	pip install pytest pytest-cov pytest-watch black flake8 mypy

# Code quality targets
.PHONY: lint
lint:
	@echo "Running linting checks..."
	flake8 $(TEST_DIR)
	mypy $(TEST_DIR)

.PHONY: format
format:
	@echo "Formatting code with black..."
	black $(TEST_DIR)

# Cleanup targets
.PHONY: clean
clean:
	@echo "Cleaning up test artifacts..."
	find $(TEST_DIR) -name "*.pyc" -delete
	find $(TEST_DIR) -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find $(TEST_DIR) -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(TEST_DIR)/htmlcov
	rm -rf $(TEST_DIR)/.coverage
	rm -rf $(TEST_DIR)/.mypy_cache
	rm -rf $(VENV_DIR)

# Quick targets
.PHONY: quick-test
quick-test:
	@echo "Running quick test suite..."
	cd $(TEST_DIR) && $(PYTHON) -m unittest test_diff_model_changes test_add_device_check test_verify_tags

# CI/CD targets
.PHONY: ci-test
ci-test:
	@echo "Running CI test suite..."
	cd $(TEST_DIR) && $(PYTHON) -m pytest --cov=../../../../../plugins/action/dtc --cov-report=xml --junit-xml=test-results.xml .

# Development targets
.PHONY: dev-setup
dev-setup: setup-venv install-deps
	@echo "Development environment setup complete!"

.PHONY: dev-test
dev-test: format lint test

# Documentation targets
.PHONY: test-docs
test-docs:
	@echo "Generating test documentation..."
	cd $(TEST_DIR) && $(PYTHON) -m pydoc -w test_*

# Utility targets
.PHONY: list-tests
list-tests:
	@echo "Available test files:"
	@find $(TEST_DIR) -name "test_*.py" | sort

.PHONY: test-count
test-count:
	@echo "Test count by file:"
	@find $(TEST_DIR) -name "test_*.py" -exec grep -c "def test_" {} \; | paste -d: <(find $(TEST_DIR) -name "test_*.py") - | sort

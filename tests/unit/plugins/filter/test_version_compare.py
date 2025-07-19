"""
Unit tests for the version_compare filter plugin.
"""

import sys
import os
import pytest
from unittest.mock import Mock, patch

from jinja2.runtime import Undefined
from jinja2.exceptions import UndefinedError

from ansible.errors import AnsibleError, AnsibleFilterError, AnsibleFilterTypeError

# Import the actual version_compare module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from plugins.filter.version_compare import version_compare, FilterModule


class TestVersionCompareFunction:
    """Test the version_compare function directly."""

    def test_version_compare_missing_packaging_library(self):
        """Test behavior when packaging library is not available."""
        # Mock the import error scenario
        with patch('plugins.filter.version_compare.PACKAGING_LIBRARY_IMPORT_ERROR', ImportError("No module named 'packaging'")):
            with pytest.raises(AnsibleError, match="packaging must be installed to use this filter plugin"):
                version_compare("1.0.0", "1.0.0", "==")

    def test_version_compare_missing_packaging_library_with_module_reload(self):
        """Test the ImportError handling during module import."""
        # This tests the import block and exception handling during module loading
        import builtins
        import importlib
        
        # Store the original import function
        original_import = builtins.__import__
        
        def mock_import(name, *args, **kwargs):
            if name == 'packaging.version':
                raise ImportError("No module named 'packaging'")
            return original_import(name, *args, **kwargs)
        
        # Mock the import and force module reload
        with patch.object(builtins, '__import__', side_effect=mock_import):
            # Remove the module from cache to force reimport
            if 'plugins.filter.version_compare' in sys.modules:
                del sys.modules['plugins.filter.version_compare']
            
            # Import the module which should trigger the ImportError handling
            import plugins.filter.version_compare as vc_module
            
            # Verify that the ImportError was captured
            assert vc_module.PACKAGING_LIBRARY_IMPORT_ERROR is not None
            assert isinstance(vc_module.PACKAGING_LIBRARY_IMPORT_ERROR, ImportError)
            
            # Test that version_compare raises AnsibleError when packaging is missing
            with pytest.raises(AnsibleError, match="packaging must be installed to use this filter plugin"):
                vc_module.version_compare("1.0.0", "1.0.0", "==")
        
        # Clean up - reimport the module normally
        if 'plugins.filter.version_compare' in sys.modules:
            del sys.modules['plugins.filter.version_compare']
        import plugins.filter.version_compare  # Reload normally

    def test_version_compare_equal(self):
        """Test equal comparison."""
        assert version_compare("1.0.0", "1.0.0", "==") is True
        assert version_compare("1.0.0", "1.0.1", "==") is False
        assert version_compare("2.1.0", "2.1.0", "==") is True

    def test_version_compare_not_equal(self):
        """Test not equal comparison."""
        assert version_compare("1.0.0", "1.0.1", "!=") is True
        assert version_compare("1.0.0", "1.0.0", "!=") is False
        assert version_compare("2.1.0", "2.0.0", "!=") is True

    def test_version_compare_greater_than(self):
        """Test greater than comparison."""
        assert version_compare("1.0.1", "1.0.0", ">") is True
        assert version_compare("1.0.0", "1.0.1", ">") is False
        assert version_compare("2.0.0", "1.9.9", ">") is True
        assert version_compare("1.0.0", "1.0.0", ">") is False

    def test_version_compare_greater_than_or_equal(self):
        """Test greater than or equal comparison."""
        assert version_compare("1.0.1", "1.0.0", ">=") is True
        assert version_compare("1.0.0", "1.0.0", ">=") is True
        assert version_compare("1.0.0", "1.0.1", ">=") is False
        assert version_compare("2.0.0", "1.9.9", ">=") is True

    def test_version_compare_less_than(self):
        """Test less than comparison."""
        assert version_compare("1.0.0", "1.0.1", "<") is True
        assert version_compare("1.0.1", "1.0.0", "<") is False
        assert version_compare("1.9.9", "2.0.0", "<") is True
        assert version_compare("1.0.0", "1.0.0", "<") is False

    def test_version_compare_less_than_or_equal(self):
        """Test less than or equal comparison."""
        assert version_compare("1.0.0", "1.0.1", "<=") is True
        assert version_compare("1.0.0", "1.0.0", "<=") is True
        assert version_compare("1.0.1", "1.0.0", "<=") is False
        assert version_compare("1.9.9", "2.0.0", "<=") is True

    def test_version_compare_complex_versions(self):
        """Test with complex version strings."""
        assert version_compare("1.0.0-alpha.1", "1.0.0-alpha.2", "<") is True
        assert version_compare("1.0.0-rc.1", "1.0.0", "<") is True
        assert version_compare("2.0.0-beta.1", "2.0.0-alpha.1", ">") is True
        assert version_compare("1.0.0.dev1", "1.0.0", "<") is True

    def test_version_compare_with_build_metadata(self):
        """Test versions with build metadata."""
        # packaging.version treats build metadata as part of the version for equality
        result = version_compare("1.0.0+build.1", "1.0.0+build.2", "==")
        assert result is False  # Different build metadata means not equal

        # But the base version comparison should still work
        assert version_compare("1.0.0+build.1", "1.0.1+build.1", "<") is True

    def test_version_compare_different_formats(self):
        """Test different version formats."""
        assert version_compare("1.0", "1.0.0", "==") is True
        assert version_compare("1", "1.0.0", "==") is True
        assert version_compare("1.0.0.0", "1.0.0", "==") is True

    def test_version_compare_version1_type_error(self):
        """Test version1 type validation."""
        with pytest.raises(AnsibleFilterTypeError, match="Can only check string versions, however version1 is"):
            version_compare(123, "1.0.0", "==")

        with pytest.raises(AnsibleFilterTypeError, match="Can only check string versions, however version1 is"):
            version_compare([], "1.0.0", "==")

        with pytest.raises(AnsibleFilterTypeError, match="Can only check string versions, however version1 is"):
            version_compare({"version": "1.0.0"}, "1.0.0", "==")

    def test_version_compare_version2_type_error(self):
        """Test version2 type validation."""
        with pytest.raises(AnsibleFilterTypeError, match="Can only check string versions, however version2 is"):
            version_compare("1.0.0", 123, "==")

        with pytest.raises(AnsibleFilterTypeError, match="Can only check string versions, however version2 is"):
            version_compare("1.0.0", [], "==")

        with pytest.raises(AnsibleFilterTypeError, match="Can only check string versions, however version2 is"):
            version_compare("1.0.0", {"version": "1.0.0"}, "==")

    def test_version_compare_operator_validation(self):
        """Test operator validation."""
        # Test unsupported operator
        with pytest.raises(AnsibleFilterError, match="Unsupported operator"):
            version_compare("1.0.0", "1.0.0", "===")

        with pytest.raises(AnsibleFilterError, match="Unsupported operator"):
            version_compare("1.0.0", "1.0.0", "~=")

    def test_version_compare_operator_type_and_content_validation(self):
        """Test operator validation with type and content checks."""
        # Test with integer operator (not string_types or Undefined)
        with pytest.raises(AnsibleFilterError, match="Unsupported operator"):
            version_compare("1.0.0", "1.0.0", 123)

        # Test with list operator (not string_types or Undefined)
        with pytest.raises(AnsibleFilterError, match="Unsupported operator"):
            version_compare("1.0.0", "1.0.0", [])

        # Test with dict operator (not string_types or Undefined)
        with pytest.raises(AnsibleFilterError, match="Unsupported operator"):
            version_compare("1.0.0", "1.0.0", {})

    def test_version_compare_undefined_version1(self):
        """Test with undefined version1."""
        undefined_mock = Mock(spec=Undefined)

        # Test that it handles Undefined properly by raising AnsibleFilterError
        with pytest.raises(AnsibleFilterError):
            version_compare(undefined_mock, "1.0.0", "==")

    def test_version_compare_undefined_version2(self):
        """Test with undefined version2."""
        undefined_mock = Mock(spec=Undefined)

        # Test that it handles Undefined properly by raising AnsibleFilterError
        with pytest.raises(AnsibleFilterError):
            version_compare("1.0.0", undefined_mock, "==")

    def test_version_compare_undefined_operator(self):
        """Test with undefined operator."""
        undefined_mock = Mock(spec=Undefined)

        # Test that it handles string-like Undefined properly
        with pytest.raises(AnsibleFilterError):
            version_compare("1.0.0", "1.0.0", undefined_mock)

    def test_version_compare_invalid_version_strings(self):
        """Test with invalid version strings."""
        with pytest.raises(AnsibleFilterError, match="Unable handle version"):
            version_compare("invalid-version", "1.0.0", "==")

        with pytest.raises(AnsibleFilterError, match="Unable handle version"):
            version_compare("1.0.0", "invalid-version", "==")

    def test_version_compare_empty_version_strings(self):
        """Test with empty version strings."""
        with pytest.raises(AnsibleFilterError, match="Unable handle version"):
            version_compare("", "1.0.0", "==")

        with pytest.raises(AnsibleFilterError, match="Unable handle version"):
            version_compare("1.0.0", "", "==")

    def test_version_compare_undefined_error_handling(self):
        """Test UndefinedError handling."""
        # This test is covered by the test_version_compare_undefined_error_during_version_creation test
        # which properly tests the UndefinedError handling in the version_compare function
        pass

    def test_version_compare_undefined_error_during_version_creation(self):
        """Test UndefinedError specifically during Version() creation."""
        # Import at module level to get the right reference
        import plugins.filter.version_compare as vc_module
        
        # Mock the Version constructor at the module level
        with patch.object(vc_module, 'Version') as mock_version:
            # Make Version constructor raise UndefinedError
            mock_version.side_effect = UndefinedError("Variable is undefined")

            # This should trigger the UndefinedError catch block which re-raises it
            with pytest.raises(UndefinedError):
                vc_module.version_compare("1.0.0", "1.0.0", "==")

    def test_version_compare_all_operators(self):
        """Test all supported operators comprehensively."""
        operators = ['==', '!=', '>', '>=', '<', '<=']

        for op in operators:
            # Test that each operator works without exception
            result = version_compare("1.0.0", "1.0.0", op)
            assert isinstance(result, bool)

    def test_version_compare_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test with very large version numbers
        assert version_compare("999.999.999", "1.0.0", ">") is True

        # Test with zero versions
        assert version_compare("0.0.0", "0.0.1", "<") is True

        # Test with single digit versions
        assert version_compare("1", "2", "<") is True

        # Test with different number of version parts
        assert version_compare("1.0", "1.0.0.0", "==") is True

    def test_version_compare_string_types_compatibility(self):
        """Test compatibility with different string types."""
        # Test with unicode strings
        assert version_compare("1.0.0", "1.0.0", "==") is True

        # Test with bytes (should fail appropriately)
        with pytest.raises(AnsibleFilterTypeError):
            version_compare(b"1.0.0", "1.0.0", "==")


class TestFilterModule:
    """Test the FilterModule class."""

    def test_filter_module_instantiation(self):
        """Test FilterModule can be instantiated."""
        filter_module = FilterModule()
        assert filter_module is not None

    def test_filter_module_filters_method(self):
        """Test filters method returns correct dictionary."""
        filter_module = FilterModule()
        filters = filter_module.filters()

        assert isinstance(filters, dict)
        assert "version_compare" in filters
        assert filters["version_compare"] is version_compare

    def test_filter_module_integration(self):
        """Test filter module integration with Ansible."""
        filter_module = FilterModule()
        filters = filter_module.filters()

        # Test that the filter function works through the module
        version_compare_func = filters["version_compare"]
        result = version_compare_func("1.0.1", "1.0.0", ">")
        assert result is True

    def test_filter_module_with_templar(self):
        """Test integration with Ansible Templar."""
        filter_module = FilterModule()
        filters = filter_module.filters()

        # Mock a basic templar environment
        mock_templar = Mock()
        mock_templar.environment = Mock()
        mock_templar.environment.filters = {}

        # Add our filter to the mock environment
        mock_templar.environment.filters.update(filters)

        # Verify the filter is available
        assert "version_compare" in mock_templar.environment.filters

    def test_filter_module_error_propagation(self):
        """Test that errors are properly propagated through the filter module."""
        filter_module = FilterModule()
        filters = filter_module.filters()
        version_compare_func = filters["version_compare"]

        # Test that errors from the underlying function are propagated
        with pytest.raises(AnsibleFilterTypeError):
            version_compare_func(123, "1.0.0", "==")

        with pytest.raises(AnsibleFilterError):
            version_compare_func("1.0.0", "1.0.0", "invalid_op")


class TestVersionCompareIntegration:
    """Integration tests for version_compare filter."""

    def test_version_compare_realistic_scenarios(self):
        """Test realistic version comparison scenarios."""
        # Common software version comparisons
        assert version_compare("12.2.2", "12.2.1", ">") is True
        assert version_compare("12.2.2", "12.2.2", ">=") is True
        assert version_compare("11.5.1", "12.0.0", "<") is True

        # NDFC version comparisons (from examples in docstring)
        assert version_compare("12.2.2", "12.2.2", ">=") is True
        assert version_compare("12.2.3", "12.2.2", ">=") is True
        assert version_compare("12.2.1", "12.2.2", ">=") is False

    def test_version_compare_with_ansible_context(self):
        """Test version_compare in a context similar to Ansible usage."""
        # Simulate Ansible variable context
        version_vars = {
            "current_version": "1.0.2",
            "required_version": "1.0.1",
            "comparison_op": ">"
        }

        result = version_compare(
            version_vars["current_version"],
            version_vars["required_version"],
            version_vars["comparison_op"]
        )
        assert result is True

    def test_version_compare_error_messages(self):
        """Test that error messages are informative."""
        # Test version1 type error message
        try:
            version_compare(123, "1.0.0", "==")
            assert False, "Should have raised AnsibleFilterTypeError"
        except AnsibleFilterTypeError as e:
            assert "version1" in str(e)
            assert "int" in str(e)

        # Test version2 type error message
        try:
            version_compare("1.0.0", 123, "==")
            assert False, "Should have raised AnsibleFilterTypeError"
        except AnsibleFilterTypeError as e:
            assert "version2" in str(e)
            assert "int" in str(e)

        # Test operator error message
        try:
            version_compare("1.0.0", "1.0.0", "invalid")
            assert False, "Should have raised AnsibleFilterError"
        except AnsibleFilterError as e:
            assert "Unsupported operator" in str(e)
            assert "invalid" in str(e)

    def test_version_compare_performance(self):
        """Test performance with multiple version comparisons."""
        import time

        # Test that version comparisons are reasonably fast
        start_time = time.time()

        for i in range(100):
            version_compare(f"1.0.{i}", f"1.0.{i+1}", "<")

        elapsed_time = time.time() - start_time
        assert elapsed_time < 1.0, f"Version comparisons took too long: {elapsed_time}s"

    def test_version_compare_memory_usage(self):
        """Test that version comparisons don't cause memory issues."""
        # Test that we can do many comparisons without memory issues
        for i in range(1000):
            result = version_compare("1.0.0", "1.0.1", "<")
            assert result is True

    def test_version_compare_documentation_examples(self):
        """Test examples from the documentation."""
        # From EXAMPLES section
        assert version_compare('1.0.2', '1.0.1', '>') is True

        # Test the conditional example scenario
        ndfc_version = "12.2.2"
        assert version_compare(ndfc_version, '12.2.2', '>=') is True


if __name__ == "__main__":
    pytest.main([__file__])

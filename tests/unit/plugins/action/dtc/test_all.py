"""
Comprehensive test suite for all DTC action plugins.
"""
import unittest
import sys
import os

# Add the collection path to sys.path
collection_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
sys.path.insert(0, collection_path)

# Import all test modules
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.test_diff_model_changes import TestDiffModelChangesActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.test_add_device_check import TestAddDeviceCheckActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.test_verify_tags import TestVerifyTagsActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.test_vpc_pair_check import TestVpcPairCheckActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.test_get_poap_data import TestGetPoapDataActionModule, TestPOAPDevice
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.test_existing_links_check import TestExistingLinksCheckActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.test_fabric_check_sync import TestFabricCheckSyncActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.test_fabrics_deploy import TestFabricsDeployActionModule


def create_full_test_suite():
    """Create a comprehensive test suite with all DTC action plugin tests."""
    suite = unittest.TestSuite()
    
    # Add test cases for each plugin
    test_classes = [
        TestDiffModelChangesActionModule,
        TestAddDeviceCheckActionModule,
        TestVerifyTagsActionModule,
        TestVpcPairCheckActionModule,
        TestPOAPDevice,
        TestGetPoapDataActionModule,
        TestExistingLinksCheckActionModule,
        TestFabricCheckSyncActionModule,
        TestFabricsDeployActionModule,
    ]
    
    for test_class in test_classes:
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(test_class))
    
    return suite


def run_all_tests():
    """Run all tests and return detailed results."""
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    suite = create_full_test_suite()
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.splitlines()[-1]}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.splitlines()[-1]}")
    
    print(f"{'='*60}")
    
    return result.wasSuccessful()


def run_specific_plugin_tests(plugin_name):
    """Run tests for a specific plugin."""
    plugin_test_map = {
        'diff_model_changes': TestDiffModelChangesActionModule,
        'add_device_check': TestAddDeviceCheckActionModule,
        'verify_tags': TestVerifyTagsActionModule,
        'vpc_pair_check': TestVpcPairCheckActionModule,
        'get_poap_data': [TestPOAPDevice, TestGetPoapDataActionModule],
        'existing_links_check': TestExistingLinksCheckActionModule,
        'fabric_check_sync': TestFabricCheckSyncActionModule,
        'fabrics_deploy': TestFabricsDeployActionModule,
    }
    
    if plugin_name not in plugin_test_map:
        print(f"Unknown plugin: {plugin_name}")
        print(f"Available plugins: {', '.join(plugin_test_map.keys())}")
        return False
    
    suite = unittest.TestSuite()
    test_classes = plugin_test_map[plugin_name]
    
    if not isinstance(test_classes, list):
        test_classes = [test_classes]
    
    for test_class in test_classes:
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(test_class))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        plugin_name = sys.argv[1]
        success = run_specific_plugin_tests(plugin_name)
    else:
        success = run_all_tests()
    
    sys.exit(0 if success else 1)

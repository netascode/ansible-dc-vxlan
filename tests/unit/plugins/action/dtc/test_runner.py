"""
Test runner for DTC action plugin tests.
"""
import unittest
import sys
import os

# Add the collection path to sys.path
collection_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
sys.path.insert(0, collection_path)

# Import test modules
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.test_diff_model_changes import TestDiffModelChangesActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.test_add_device_check import TestAddDeviceCheckActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.test_verify_tags import TestVerifyTagsActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.test_vpc_pair_check import TestVpcPairCheckActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.test_get_poap_data import TestGetPoapDataActionModule, TestPOAPDevice
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.test_existing_links_check import TestExistingLinksCheckActionModule
from ansible_collections.cisco.nac_dc_vxlan.tests.unit.plugins.action.dtc.test_fabric_check_sync import TestFabricCheckSyncActionModule


def create_test_suite():
    """Create a test suite with all DTC action plugin tests."""
    suite = unittest.TestSuite()
    
    # Add test cases for each plugin
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDiffModelChangesActionModule))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAddDeviceCheckActionModule))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestVerifyTagsActionModule))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestVpcPairCheckActionModule))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPOAPDevice))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGetPoapDataActionModule))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestExistingLinksCheckActionModule))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFabricCheckSyncActionModule))
    
    return suite


def run_tests():
    """Run all tests and return results."""
    runner = unittest.TextTestRunner(verbosity=2)
    suite = create_test_suite()
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

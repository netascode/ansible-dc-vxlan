"""
Unit tests for the helper_functions plugin_utils module.
"""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add plugin_utils to Python path
sys.path.insert(0, '/Users/mtarking/Documents/Development/DCN/nac-vxlan-as-code/vxlan-as-code/collections/ansible_collections/cisco/nac_dc_vxlan/plugins/plugin_utils')

try:
    from helper_functions import (
        data_model_key_check,
        hostname_to_ip_mapping,
        ndfc_get_switch_policy,
        ndfc_get_switch_policy_using_template,
        ndfc_get_switch_policy_using_desc,
        ndfc_get_fabric_attributes,
        ndfc_get_fabric_switches
    )
except ImportError:
    # Alternative import path for testing
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "helper_functions",
        "/Users/mtarking/Documents/Development/DCN/nac-vxlan-as-code/vxlan-as-code/collections/ansible_collections/cisco/nac_dc_vxlan/plugins/plugin_utils/helper_functions.py"
    )
    helper_functions_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper_functions_module)
    
    data_model_key_check = helper_functions_module.data_model_key_check
    hostname_to_ip_mapping = helper_functions_module.hostname_to_ip_mapping
    ndfc_get_switch_policy = helper_functions_module.ndfc_get_switch_policy
    ndfc_get_switch_policy_using_template = helper_functions_module.ndfc_get_switch_policy_using_template
    ndfc_get_switch_policy_using_desc = helper_functions_module.ndfc_get_switch_policy_using_desc
    ndfc_get_fabric_attributes = helper_functions_module.ndfc_get_fabric_attributes
    ndfc_get_fabric_switches = helper_functions_module.ndfc_get_fabric_switches


class TestDataModelKeyCheck:
    """Test the data_model_key_check function."""

    def test_data_model_key_check_all_keys_found_with_data(self):
        """Test when all keys are found and contain data."""
        tested_object = {
            'vxlan': {
                'global': {
                    'dns_servers': ['8.8.8.8', '8.8.4.4']
                }
            }
        }
        keys = ['vxlan', 'global', 'dns_servers']
        
        result = data_model_key_check(tested_object, keys)
        
        assert result['keys_found'] == ['vxlan', 'global', 'dns_servers']
        assert result['keys_not_found'] == []
        assert result['keys_data'] == ['vxlan', 'global', 'dns_servers']
        assert result['keys_no_data'] == []

    def test_data_model_key_check_all_keys_found_with_empty_data(self):
        """Test when all keys are found but some contain no data."""
        tested_object = {
            'vxlan': {
                'global': {
                    'dns_servers': []
                }
            }
        }
        keys = ['vxlan', 'global', 'dns_servers']
        
        result = data_model_key_check(tested_object, keys)
        
        assert result['keys_found'] == ['vxlan', 'global', 'dns_servers']
        assert result['keys_not_found'] == []
        assert result['keys_data'] == ['vxlan', 'global']
        assert result['keys_no_data'] == ['dns_servers']

    def test_data_model_key_check_some_keys_not_found(self):
        """Test when some keys are not found."""
        tested_object = {
            'vxlan': {
                'global': {}
            }
        }
        keys = ['vxlan', 'global', 'dns_servers']
        
        result = data_model_key_check(tested_object, keys)
        
        assert result['keys_found'] == ['vxlan', 'global']
        assert result['keys_not_found'] == ['dns_servers']
        assert result['keys_data'] == ['vxlan']
        assert result['keys_no_data'] == ['global']

    def test_data_model_key_check_no_keys_found(self):
        """Test when no keys are found."""
        tested_object = {}
        keys = ['vxlan', 'global', 'dns_servers']
        
        result = data_model_key_check(tested_object, keys)
        
        assert result['keys_found'] == []
        assert result['keys_not_found'] == ['vxlan', 'global', 'dns_servers']
        assert result['keys_data'] == []
        assert result['keys_no_data'] == []

    def test_data_model_key_check_empty_keys_list(self):
        """Test with empty keys list."""
        tested_object = {'vxlan': {'global': {}}}
        keys = []
        
        result = data_model_key_check(tested_object, keys)
        
        assert result['keys_found'] == []
        assert result['keys_not_found'] == []
        assert result['keys_data'] == []
        assert result['keys_no_data'] == []

    def test_data_model_key_check_none_tested_object(self):
        """Test with None tested_object."""
        tested_object = None
        keys = ['vxlan', 'global']
        
        result = data_model_key_check(tested_object, keys)
        
        assert result['keys_found'] == []
        assert result['keys_not_found'] == ['vxlan', 'global']
        assert result['keys_data'] == []
        assert result['keys_no_data'] == []

    def test_data_model_key_check_single_key(self):
        """Test with a single key."""
        tested_object = {'vxlan': {'data': 'test'}}
        keys = ['vxlan']
        
        result = data_model_key_check(tested_object, keys)
        
        assert result['keys_found'] == ['vxlan']
        assert result['keys_not_found'] == []
        assert result['keys_data'] == ['vxlan']
        assert result['keys_no_data'] == []

    def test_data_model_key_check_nested_empty_objects(self):
        """Test with nested empty objects."""
        tested_object = {
            'vxlan': {
                'global': {
                    'dns_servers': {
                        'primary': None
                    }
                }
            }
        }
        keys = ['vxlan', 'global', 'dns_servers', 'primary']
        
        result = data_model_key_check(tested_object, keys)
        
        assert result['keys_found'] == ['vxlan', 'global', 'dns_servers', 'primary']
        assert result['keys_not_found'] == []
        assert result['keys_data'] == ['vxlan', 'global', 'dns_servers']
        assert result['keys_no_data'] == ['primary']


class TestHostnameToIpMapping:
    """Test the hostname_to_ip_mapping function."""

    def test_hostname_to_ip_mapping_ipv4(self):
        """Test hostname to IPv4 mapping."""
        model_data = {
            'vxlan': {
                'topology': {
                    'switches': [
                        {
                            'name': 'leaf-01',
                            'management': {
                                'management_ipv4_address': '192.168.1.10'
                            }
                        },
                        {
                            'name': 'leaf-02',
                            'management': {
                                'management_ipv4_address': '192.168.1.11'
                            }
                        }
                    ]
                },
                'policy': {
                    'switches': [
                        {'name': 'leaf-01'},
                        {'name': 'leaf-02'}
                    ]
                }
            }
        }
        
        result = hostname_to_ip_mapping(model_data)
        
        assert result['vxlan']['policy']['switches'][0]['mgmt_ip_address'] == '192.168.1.10'
        assert result['vxlan']['policy']['switches'][1]['mgmt_ip_address'] == '192.168.1.11'

    def test_hostname_to_ip_mapping_ipv6(self):
        """Test hostname to IPv6 mapping."""
        model_data = {
            'vxlan': {
                'topology': {
                    'switches': [
                        {
                            'name': 'leaf-01',
                            'management': {
                                'management_ipv6_address': '2001:db8::10'
                            }
                        }
                    ]
                },
                'policy': {
                    'switches': [
                        {'name': 'leaf-01'}
                    ]
                }
            }
        }
        
        result = hostname_to_ip_mapping(model_data)
        
        assert result['vxlan']['policy']['switches'][0]['mgmt_ip_address'] == '2001:db8::10'

    def test_hostname_to_ip_mapping_ipv4_preferred_over_ipv6(self):
        """Test that IPv4 is preferred over IPv6 when both exist."""
        model_data = {
            'vxlan': {
                'topology': {
                    'switches': [
                        {
                            'name': 'leaf-01',
                            'management': {
                                'management_ipv4_address': '192.168.1.10',
                                'management_ipv6_address': '2001:db8::10'
                            }
                        }
                    ]
                },
                'policy': {
                    'switches': [
                        {'name': 'leaf-01'}
                    ]
                }
            }
        }
        
        result = hostname_to_ip_mapping(model_data)
        
        assert result['vxlan']['policy']['switches'][0]['mgmt_ip_address'] == '192.168.1.10'

    def test_hostname_to_ip_mapping_no_matching_topology_switch(self):
        """Test when policy switch doesn't exist in topology."""
        model_data = {
            'vxlan': {
                'topology': {
                    'switches': [
                        {
                            'name': 'leaf-01',
                            'management': {
                                'management_ipv4_address': '192.168.1.10'
                            }
                        }
                    ]
                },
                'policy': {
                    'switches': [
                        {'name': 'leaf-02'}
                    ]
                }
            }
        }
        
        result = hostname_to_ip_mapping(model_data)
        
        assert 'mgmt_ip_address' not in result['vxlan']['policy']['switches'][0]

    def test_hostname_to_ip_mapping_no_management_ip(self):
        """Test when topology switch has no management IP."""
        model_data = {
            'vxlan': {
                'topology': {
                    'switches': [
                        {
                            'name': 'leaf-01',
                            'management': {}
                        }
                    ]
                },
                'policy': {
                    'switches': [
                        {'name': 'leaf-01'}
                    ]
                }
            }
        }
        
        result = hostname_to_ip_mapping(model_data)
        
        assert 'mgmt_ip_address' not in result['vxlan']['policy']['switches'][0]

    def test_hostname_to_ip_mapping_empty_switches(self):
        """Test with empty switches lists."""
        model_data = {
            'vxlan': {
                'topology': {
                    'switches': []
                },
                'policy': {
                    'switches': []
                }
            }
        }
        
        result = hostname_to_ip_mapping(model_data)
        
        assert result['vxlan']['policy']['switches'] == []

    def test_hostname_to_ip_mapping_preserves_existing_data(self):
        """Test that existing data is preserved."""
        model_data = {
            'vxlan': {
                'topology': {
                    'switches': [
                        {
                            'name': 'leaf-01',
                            'management': {
                                'management_ipv4_address': '192.168.1.10'
                            }
                        }
                    ]
                },
                'policy': {
                    'switches': [
                        {
                            'name': 'leaf-01',
                            'existing_field': 'existing_value'
                        }
                    ]
                }
            }
        }
        
        result = hostname_to_ip_mapping(model_data)
        
        assert result['vxlan']['policy']['switches'][0]['mgmt_ip_address'] == '192.168.1.10'
        assert result['vxlan']['policy']['switches'][0]['existing_field'] == 'existing_value'


class TestNdfc_GetSwitchPolicy:
    """Test the ndfc_get_switch_policy function."""

    def test_ndfc_get_switch_policy_success(self):
        """Test successful switch policy retrieval."""
        mock_self = Mock()
        mock_self._execute_module.return_value = {
            'response': {
                'DATA': [
                    {
                        'serialNumber': 'ABC123',
                        'templateName': 'leaf_template',
                        'policy': 'test_policy'
                    }
                ]
            }
        }
        
        task_vars = {'ansible_host': 'test_host'}
        tmp = None
        switch_serial = 'ABC123'
        
        result = ndfc_get_switch_policy(mock_self, task_vars, tmp, switch_serial)
        
        mock_self._execute_module.assert_called_once_with(
            module_name="cisco.dcnm.dcnm_rest",
            module_args={
                "method": "GET",
                "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/policies/switches/{switch_serial}/SWITCH/SWITCH"
            },
            task_vars=task_vars,
            tmp=tmp
        )
        
        assert result['response']['DATA'][0]['serialNumber'] == 'ABC123'

    def test_ndfc_get_switch_policy_module_call_parameters(self):
        """Test that module is called with correct parameters."""
        mock_self = Mock()
        mock_self._execute_module.return_value = {'response': {'DATA': []}}
        
        task_vars = {'test_var': 'test_value'}
        tmp = 'test_tmp'
        switch_serial = 'XYZ789'
        
        ndfc_get_switch_policy(mock_self, task_vars, tmp, switch_serial)
        
        expected_path = f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/policies/switches/{switch_serial}/SWITCH/SWITCH"
        mock_self._execute_module.assert_called_once_with(
            module_name="cisco.dcnm.dcnm_rest",
            module_args={
                "method": "GET",
                "path": expected_path
            },
            task_vars=task_vars,
            tmp=tmp
        )


class TestNdfc_GetSwitchPolicyUsingTemplate:
    """Test the ndfc_get_switch_policy_using_template function."""

    def test_ndfc_get_switch_policy_using_template_success(self):
        """Test successful policy retrieval using template."""
        mock_self = Mock()
        
        # Mock the response from ndfc_get_switch_policy
        with patch('helper_functions.ndfc_get_switch_policy') as mock_get_policy:
            mock_get_policy.return_value = {
                'response': {
                    'DATA': [
                        {
                            'serialNumber': 'ABC123',
                            'templateName': 'leaf_template',
                            'policy': 'test_policy'
                        },
                        {
                            'serialNumber': 'ABC123',
                            'templateName': 'spine_template',
                            'policy': 'other_policy'
                        }
                    ]
                }
            }
            
            task_vars = {'ansible_host': 'test_host'}
            tmp = None
            switch_serial = 'ABC123'
            template_name = 'leaf_template'
            
            result = ndfc_get_switch_policy_using_template(mock_self, task_vars, tmp, switch_serial, template_name)
            
            mock_get_policy.assert_called_once_with(mock_self, task_vars, tmp, switch_serial)
            assert result['serialNumber'] == 'ABC123'
            assert result['templateName'] == 'leaf_template'
            assert result['policy'] == 'test_policy'

    def test_ndfc_get_switch_policy_using_template_not_found(self):
        """Test when template is not found."""
        mock_self = Mock()
        
        with patch('helper_functions.ndfc_get_switch_policy') as mock_get_policy:
            mock_get_policy.return_value = {
                'response': {
                    'DATA': [
                        {
                            'serialNumber': 'ABC123',
                            'templateName': 'spine_template',
                            'policy': 'other_policy'
                        }
                    ]
                }
            }
            
            task_vars = {'ansible_host': 'test_host'}
            tmp = None
            switch_serial = 'ABC123'
            template_name = 'leaf_template'
            
            with pytest.raises(Exception) as exc_info:
                ndfc_get_switch_policy_using_template(mock_self, task_vars, tmp, switch_serial, template_name)
            
            assert "Policy for template leaf_template and switch ABC123 not found!" in str(exc_info.value)
            assert "Please ensure switch with serial number ABC123 is part of the fabric." in str(exc_info.value)

    def test_ndfc_get_switch_policy_using_template_wrong_serial(self):
        """Test when switch serial doesn't match."""
        mock_self = Mock()
        
        with patch('helper_functions.ndfc_get_switch_policy') as mock_get_policy:
            mock_get_policy.return_value = {
                'response': {
                    'DATA': [
                        {
                            'serialNumber': 'XYZ789',
                            'templateName': 'leaf_template',
                            'policy': 'test_policy'
                        }
                    ]
                }
            }
            
            task_vars = {'ansible_host': 'test_host'}
            tmp = None
            switch_serial = 'ABC123'
            template_name = 'leaf_template'
            
            with pytest.raises(Exception) as exc_info:
                ndfc_get_switch_policy_using_template(mock_self, task_vars, tmp, switch_serial, template_name)
            
            assert "Policy for template leaf_template and switch ABC123 not found!" in str(exc_info.value)


class TestNdfc_GetSwitchPolicyUsingDesc:
    """Test the ndfc_get_switch_policy_using_desc function."""

    def test_ndfc_get_switch_policy_using_desc_success(self):
        """Test successful policy retrieval using description."""
        mock_self = Mock()
        
        with patch('helper_functions.ndfc_get_switch_policy') as mock_get_policy:
            mock_get_policy.return_value = {
                'response': {
                    'DATA': [
                        {
                            'serialNumber': 'ABC123',
                            'templateName': 'leaf_template',
                            'description': 'nac-generated policy',
                            'source': '',
                            'policy': 'test_policy'
                        },
                        {
                            'serialNumber': 'ABC123',
                            'templateName': 'spine_template',
                            'description': 'manual policy',
                            'source': 'manual',
                            'policy': 'other_policy'
                        }
                    ]
                }
            }
            
            task_vars = {'ansible_host': 'test_host'}
            tmp = None
            switch_serial = 'ABC123'
            prefix = 'nac'
            
            result = ndfc_get_switch_policy_using_desc(mock_self, task_vars, tmp, switch_serial, prefix)
            
            mock_get_policy.assert_called_once_with(mock_self, task_vars, tmp, switch_serial)
            assert len(result) == 1
            assert result[0]['templateName'] == 'leaf_template'
            assert result[0]['description'] == 'nac-generated policy'
            assert result[0]['source'] == ''

    def test_ndfc_get_switch_policy_using_desc_no_matches(self):
        """Test when no policies match the description prefix."""
        mock_self = Mock()
        
        with patch('helper_functions.ndfc_get_switch_policy') as mock_get_policy:
            mock_get_policy.return_value = {
                'response': {
                    'DATA': [
                        {
                            'serialNumber': 'ABC123',
                            'templateName': 'leaf_template',
                            'description': 'manual policy',
                            'source': 'manual',
                            'policy': 'test_policy'
                        }
                    ]
                }
            }
            
            task_vars = {'ansible_host': 'test_host'}
            tmp = None
            switch_serial = 'ABC123'
            prefix = 'nac'
            
            result = ndfc_get_switch_policy_using_desc(mock_self, task_vars, tmp, switch_serial, prefix)
            
            assert result == []

    def test_ndfc_get_switch_policy_using_desc_no_description(self):
        """Test when policies have no description."""
        mock_self = Mock()
        
        with patch('helper_functions.ndfc_get_switch_policy') as mock_get_policy:
            mock_get_policy.return_value = {
                'response': {
                    'DATA': [
                        {
                            'serialNumber': 'ABC123',
                            'templateName': 'leaf_template',
                            'source': '',
                            'policy': 'test_policy'
                        }
                    ]
                }
            }
            
            task_vars = {'ansible_host': 'test_host'}
            tmp = None
            switch_serial = 'ABC123'
            prefix = 'nac'
            
            result = ndfc_get_switch_policy_using_desc(mock_self, task_vars, tmp, switch_serial, prefix)
            
            assert result == []

    def test_ndfc_get_switch_policy_using_desc_non_empty_source(self):
        """Test that policies with non-empty source are filtered out."""
        mock_self = Mock()
        
        with patch('helper_functions.ndfc_get_switch_policy') as mock_get_policy:
            mock_get_policy.return_value = {
                'response': {
                    'DATA': [
                        {
                            'serialNumber': 'ABC123',
                            'templateName': 'leaf_template',
                            'description': 'nac-generated policy',
                            'source': 'manual',
                            'policy': 'test_policy'
                        }
                    ]
                }
            }
            
            task_vars = {'ansible_host': 'test_host'}
            tmp = None
            switch_serial = 'ABC123'
            prefix = 'nac'
            
            result = ndfc_get_switch_policy_using_desc(mock_self, task_vars, tmp, switch_serial, prefix)
            
            assert result == []


class TestNdfc_GetFabricAttributes:
    """Test the ndfc_get_fabric_attributes function."""

    def test_ndfc_get_fabric_attributes_success(self):
        """Test successful fabric attributes retrieval."""
        mock_self = Mock()
        mock_self._execute_module.return_value = {
            'response': {
                'DATA': {
                    'nvPairs': {
                        'FABRIC_NAME': 'test_fabric',
                        'BGP_AS': '65000',
                        'ANYCAST_GW_MAC': '0000.1111.2222'
                    }
                }
            }
        }
        
        task_vars = {'ansible_host': 'test_host'}
        tmp = None
        fabric = 'test_fabric'
        
        result = ndfc_get_fabric_attributes(mock_self, task_vars, tmp, fabric)
        
        mock_self._execute_module.assert_called_once_with(
            module_name="cisco.dcnm.dcnm_rest",
            module_args={
                "method": "GET",
                "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/{fabric}",
            },
            task_vars=task_vars,
            tmp=tmp
        )
        
        assert result['FABRIC_NAME'] == 'test_fabric'
        assert result['BGP_AS'] == '65000'
        assert result['ANYCAST_GW_MAC'] == '0000.1111.2222'

    def test_ndfc_get_fabric_attributes_module_call_parameters(self):
        """Test that module is called with correct parameters."""
        mock_self = Mock()
        mock_self._execute_module.return_value = {
            'response': {
                'DATA': {
                    'nvPairs': {}
                }
            }
        }
        
        task_vars = {'test_var': 'test_value'}
        tmp = 'test_tmp'
        fabric = 'production_fabric'
        
        ndfc_get_fabric_attributes(mock_self, task_vars, tmp, fabric)
        
        expected_path = f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/{fabric}"
        mock_self._execute_module.assert_called_once_with(
            module_name="cisco.dcnm.dcnm_rest",
            module_args={
                "method": "GET",
                "path": expected_path,
            },
            task_vars=task_vars,
            tmp=tmp
        )


class TestNdfc_GetFabricSwitches:
    """Test the ndfc_get_fabric_switches function."""

    def test_ndfc_get_fabric_switches_success(self):
        """Test successful fabric switches retrieval."""
        mock_self = Mock()
        mock_self._execute_module.return_value = {
            'response': [
                {
                    'hostName': 'leaf-01',
                    'ipAddress': '192.168.1.10',
                    'serialNumber': 'ABC123'
                },
                {
                    'hostName': 'leaf-02',
                    'ipAddress': '192.168.1.11',
                    'serialNumber': 'XYZ789'
                }
            ]
        }
        
        task_vars = {'ansible_host': 'test_host'}
        tmp = None
        fabric = 'test_fabric'
        
        result = ndfc_get_fabric_switches(mock_self, task_vars, tmp, fabric)
        
        mock_self._execute_module.assert_called_once_with(
            module_name="cisco.dcnm.dcnm_inventory",
            module_args={
                "fabric": fabric,
                "state": "query"
            },
            task_vars=task_vars,
            tmp=tmp
        )
        
        assert len(result) == 2
        assert result[0]['hostname'] == 'leaf-01'
        assert result[0]['mgmt_ip_address'] == '192.168.1.10'
        assert result[1]['hostname'] == 'leaf-02'
        assert result[1]['mgmt_ip_address'] == '192.168.1.11'

    def test_ndfc_get_fabric_switches_no_hostname(self):
        """Test fabric switches without hostname are filtered out."""
        mock_self = Mock()
        mock_self._execute_module.return_value = {
            'response': [
                {
                    'hostName': 'leaf-01',
                    'ipAddress': '192.168.1.10',
                    'serialNumber': 'ABC123'
                },
                {
                    'ipAddress': '192.168.1.11',
                    'serialNumber': 'XYZ789'
                }
            ]
        }
        
        task_vars = {'ansible_host': 'test_host'}
        tmp = None
        fabric = 'test_fabric'
        
        result = ndfc_get_fabric_switches(mock_self, task_vars, tmp, fabric)
        
        assert len(result) == 1
        assert result[0]['hostname'] == 'leaf-01'
        assert result[0]['mgmt_ip_address'] == '192.168.1.10'

    def test_ndfc_get_fabric_switches_empty_response(self):
        """Test with empty response."""
        mock_self = Mock()
        mock_self._execute_module.return_value = {
            'response': []
        }
        
        task_vars = {'ansible_host': 'test_host'}
        tmp = None
        fabric = 'test_fabric'
        
        result = ndfc_get_fabric_switches(mock_self, task_vars, tmp, fabric)
        
        assert result == []

    def test_ndfc_get_fabric_switches_module_call_parameters(self):
        """Test that module is called with correct parameters."""
        mock_self = Mock()
        mock_self._execute_module.return_value = {'response': []}
        
        task_vars = {'test_var': 'test_value'}
        tmp = 'test_tmp'
        fabric = 'production_fabric'
        
        ndfc_get_fabric_switches(mock_self, task_vars, tmp, fabric)
        
        mock_self._execute_module.assert_called_once_with(
            module_name="cisco.dcnm.dcnm_inventory",
            module_args={
                "fabric": fabric,
                "state": "query"
            },
            task_vars=task_vars,
            tmp=tmp
        )


class TestHelperFunctionsIntegration:
    """Integration tests for helper functions."""

    def test_data_model_key_check_integration(self):
        """Test data_model_key_check with realistic data model."""
        realistic_model = {
            'vxlan': {
                'global': {
                    'dns_servers': ['8.8.8.8', '8.8.4.4'],
                    'ntp_servers': [],
                    'spanning_tree': {
                        'mode': 'mst'
                    }
                },
                'topology': {
                    'switches': [
                        {'name': 'leaf-01', 'role': 'leaf'},
                        {'name': 'spine-01', 'role': 'spine'}
                    ]
                }
            }
        }
        
        # Test found keys with data
        keys = ['vxlan', 'global', 'dns_servers']
        result = data_model_key_check(realistic_model, keys)
        assert result['keys_found'] == keys
        assert result['keys_data'] == keys
        
        # Test found keys without data
        keys = ['vxlan', 'global', 'ntp_servers']
        result = data_model_key_check(realistic_model, keys)
        assert result['keys_found'] == keys
        assert result['keys_data'] == ['vxlan', 'global']
        assert result['keys_no_data'] == ['ntp_servers']

    def test_hostname_to_ip_mapping_integration(self):
        """Test hostname_to_ip_mapping with realistic data model."""
        realistic_model = {
            'vxlan': {
                'topology': {
                    'switches': [
                        {
                            'name': 'leaf-01',
                            'role': 'leaf',
                            'management': {
                                'management_ipv4_address': '192.168.1.10'
                            }
                        },
                        {
                            'name': 'spine-01',
                            'role': 'spine',
                            'management': {
                                'management_ipv6_address': '2001:db8::20'
                            }
                        }
                    ]
                },
                'policy': {
                    'switches': [
                        {
                            'name': 'leaf-01',
                            'policies': ['leaf_policy']
                        },
                        {
                            'name': 'spine-01',
                            'policies': ['spine_policy']
                        }
                    ]
                }
            }
        }
        
        result = hostname_to_ip_mapping(realistic_model)
        
        # Check that IPv4 mapping was added
        leaf_switch = next(s for s in result['vxlan']['policy']['switches'] if s['name'] == 'leaf-01')
        assert leaf_switch['mgmt_ip_address'] == '192.168.1.10'
        
        # Check that IPv6 mapping was added
        spine_switch = next(s for s in result['vxlan']['policy']['switches'] if s['name'] == 'spine-01')
        assert spine_switch['mgmt_ip_address'] == '2001:db8::20'
        
        # Check that existing data was preserved
        assert leaf_switch['policies'] == ['leaf_policy']
        assert spine_switch['policies'] == ['spine_policy']


if __name__ == "__main__":
    pytest.main([__file__])

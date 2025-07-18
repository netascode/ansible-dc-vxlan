"""
Unit tests for the data_model_keys plugin_utils module.
"""

import sys
import os
import pytest

# Add plugin_utils to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'plugins', 'plugin_utils'))

try:
    from data_model_keys import root_key, model_keys
except ImportError:
    # Alternative import path for testing
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "data_model_keys",
        os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'plugins', 'plugin_utils', 'data_model_keys.py')
    )
    data_model_keys_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(data_model_keys_module)

    root_key = data_model_keys_module.root_key
    model_keys = data_model_keys_module.model_keys


class TestRootKey:
    """Test the root_key constant."""

    def test_root_key_value(self):
        """Test that root_key is set to 'vxlan'."""
        assert root_key == 'vxlan'

    def test_root_key_type(self):
        """Test that root_key is a string."""
        assert isinstance(root_key, str)


class TestModelKeysStructure:
    """Test the overall structure of model_keys."""

    def test_model_keys_is_dict(self):
        """Test that model_keys is a dictionary."""
        assert isinstance(model_keys, dict)

    def test_model_keys_fabric_types(self):
        """Test that model_keys contains all expected fabric types."""
        expected_fabric_types = ['VXLAN_EVPN', 'MSD', 'MCF', 'ISN', 'External']

        for fabric_type in expected_fabric_types:
            assert fabric_type in model_keys
            assert isinstance(model_keys[fabric_type], dict)

    def test_model_keys_fabric_types_count(self):
        """Test that model_keys contains exactly the expected number of fabric types."""
        assert len(model_keys) == 5

    def test_model_keys_all_values_are_dicts(self):
        """Test that all top-level values in model_keys are dictionaries."""
        for fabric_type, fabric_keys in model_keys.items():
            assert isinstance(fabric_keys, dict), f"model_keys['{fabric_type}'] should be a dict"


class TestVxlanEvpnKeys:
    """Test the VXLAN_EVPN fabric type keys."""

    def test_vxlan_evpn_global_keys(self):
        """Test VXLAN_EVPN global keys."""
        vxlan_evpn = model_keys['VXLAN_EVPN']

        # Test basic global key
        assert 'global' in vxlan_evpn
        assert vxlan_evpn['global'] == [root_key, 'global', 'KEY']

        # Test global subkeys
        assert 'global.dns_servers' in vxlan_evpn
        assert vxlan_evpn['global.dns_servers'] == [root_key, 'global', 'dns_servers', 'LIST']

        assert 'global.ntp_servers' in vxlan_evpn
        assert vxlan_evpn['global.ntp_servers'] == [root_key, 'global', 'ntp_servers', 'LIST']

        assert 'global.syslog_servers' in vxlan_evpn
        assert vxlan_evpn['global.syslog_servers'] == [root_key, 'global', 'syslog_servers', 'LIST']

    def test_vxlan_evpn_netflow_keys(self):
        """Test VXLAN_EVPN netflow keys."""
        vxlan_evpn = model_keys['VXLAN_EVPN']

        assert 'global.netflow' in vxlan_evpn
        assert vxlan_evpn['global.netflow'] == [root_key, 'global', 'netflow', 'KEY']

        assert 'global.netflow.exporter' in vxlan_evpn
        assert vxlan_evpn['global.netflow.exporter'] == [root_key, 'global', 'netflow', 'exporter', 'LIST']

        assert 'global.netflow.record' in vxlan_evpn
        assert vxlan_evpn['global.netflow.record'] == [root_key, 'global', 'netflow', 'record', 'LIST']

        assert 'global.netflow.monitor' in vxlan_evpn
        assert vxlan_evpn['global.netflow.monitor'] == [root_key, 'global', 'netflow', 'monitor', 'LIST']

    def test_vxlan_evpn_spanning_tree_keys(self):
        """Test VXLAN_EVPN spanning tree keys."""
        vxlan_evpn = model_keys['VXLAN_EVPN']

        assert 'global.spanning_tree' in vxlan_evpn
        assert vxlan_evpn['global.spanning_tree'] == [root_key, 'global', 'spanning_tree', 'KEY']

    def test_vxlan_evpn_underlay_keys(self):
        """Test VXLAN_EVPN underlay keys."""
        vxlan_evpn = model_keys['VXLAN_EVPN']

        assert 'underlay' in vxlan_evpn
        assert vxlan_evpn['underlay'] == [root_key, 'underlay', 'KEY']

    def test_vxlan_evpn_topology_keys(self):
        """Test VXLAN_EVPN topology keys."""
        vxlan_evpn = model_keys['VXLAN_EVPN']

        assert 'topology' in vxlan_evpn
        assert vxlan_evpn['topology'] == [root_key, 'topology', 'KEY']

        assert 'topology.edge_connections' in vxlan_evpn
        assert vxlan_evpn['topology.edge_connections'] == [root_key, 'topology', 'edge_connections', 'LIST']

        assert 'topology.fabric_links' in vxlan_evpn
        assert vxlan_evpn['topology.fabric_links'] == [root_key, 'topology', 'fabric_links', 'LIST']

        assert 'topology.switches' in vxlan_evpn
        assert vxlan_evpn['topology.switches'] == [root_key, 'topology', 'switches', 'LIST']

        assert 'topology.switches.freeform' in vxlan_evpn
        assert vxlan_evpn['topology.switches.freeform'] == [root_key, 'topology', 'switches', 'freeform', 'LIST_INDEX']

        assert 'topology.switches.interfaces' in vxlan_evpn
        assert vxlan_evpn['topology.switches.interfaces'] == [root_key, 'topology', 'switches', 'interfaces', 'LIST_INDEX']

        assert 'topology.vpc_peers' in vxlan_evpn
        assert vxlan_evpn['topology.vpc_peers'] == [root_key, 'topology', 'vpc_peers', 'LIST']

    def test_vxlan_evpn_overlay_keys(self):
        """Test VXLAN_EVPN overlay keys."""
        vxlan_evpn = model_keys['VXLAN_EVPN']

        assert 'overlay' in vxlan_evpn
        assert vxlan_evpn['overlay'] == [root_key, 'overlay', 'KEY']

        assert 'overlay.vrfs' in vxlan_evpn
        assert vxlan_evpn['overlay.vrfs'] == [root_key, 'overlay', 'vrfs', 'LIST']

        assert 'overlay.vrf_attach_groups' in vxlan_evpn
        assert vxlan_evpn['overlay.vrf_attach_groups'] == [root_key, 'overlay', 'vrf_attach_groups', 'LIST']

        assert 'overlay.vrf_attach_groups.switches' in vxlan_evpn
        assert vxlan_evpn['overlay.vrf_attach_groups.switches'] == [root_key, 'overlay', 'vrf_attach_groups', 'switches', 'LIST_INDEX']

        assert 'overlay.networks' in vxlan_evpn
        assert vxlan_evpn['overlay.networks'] == [root_key, 'overlay', 'networks', 'LIST']

        assert 'overlay.network_attach_groups' in vxlan_evpn
        assert vxlan_evpn['overlay.network_attach_groups'] == [root_key, 'overlay', 'network_attach_groups', 'LIST']

        assert 'overlay.network_attach_groups.switches' in vxlan_evpn
        assert vxlan_evpn['overlay.network_attach_groups.switches'] == [root_key, 'overlay', 'network_attach_groups', 'switches', 'LIST_INDEX']

    def test_vxlan_evpn_overlay_extensions_keys(self):
        """Test VXLAN_EVPN overlay extensions keys."""
        vxlan_evpn = model_keys['VXLAN_EVPN']

        assert 'overlay_extensions' in vxlan_evpn
        assert vxlan_evpn['overlay_extensions'] == [root_key, 'overlay_extensions', 'KEY']

        assert 'overlay_extensions.route_control' in vxlan_evpn
        assert vxlan_evpn['overlay_extensions.route_control'] == [root_key, 'overlay_extensions', 'route_control', 'KEY']

        assert 'overlay_extensions.route_control.route_maps' in vxlan_evpn
        assert vxlan_evpn['overlay_extensions.route_control.route_maps'] == [root_key, 'overlay_extensions', 'route_control', 'route_maps', 'LIST']

    def test_vxlan_evpn_policy_keys(self):
        """Test VXLAN_EVPN policy keys."""
        vxlan_evpn = model_keys['VXLAN_EVPN']

        assert 'policy' in vxlan_evpn
        assert vxlan_evpn['policy'] == [root_key, 'policy', 'KEY']

        assert 'policy.policies' in vxlan_evpn
        assert vxlan_evpn['policy.policies'] == [root_key, 'policy', 'policies', 'LIST']

        assert 'policy.groups' in vxlan_evpn
        assert vxlan_evpn['policy.groups'] == [root_key, 'policy', 'groups', 'LIST']

        assert 'policy.switches' in vxlan_evpn
        assert vxlan_evpn['policy.switches'] == [root_key, 'policy', 'switches', 'LIST']


class TestIsnKeys:
    """Test the ISN fabric type keys."""

    def test_isn_topology_keys(self):
        """Test ISN topology keys."""
        isn = model_keys['ISN']

        assert 'topology' in isn
        assert isn['topology'] == [root_key, 'topology', 'KEY']

        assert 'topology.edge_connections' in isn
        assert isn['topology.edge_connections'] == [root_key, 'topology', 'edge_connections', 'LIST']

        assert 'topology.fabric_links' in isn
        assert isn['topology.fabric_links'] == [root_key, 'topology', 'fabric_links', 'LIST']

        assert 'topology.switches' in isn
        assert isn['topology.switches'] == [root_key, 'topology', 'switches', 'LIST']

        assert 'topology.switches.freeform' in isn
        assert isn['topology.switches.freeform'] == [root_key, 'topology', 'switches', 'freeform', 'LIST_INDEX']

        assert 'topology.switches.interfaces' in isn
        assert isn['topology.switches.interfaces'] == [root_key, 'topology', 'switches', 'interfaces', 'LIST_INDEX']

        assert 'topology.vpc_peers' in isn
        assert isn['topology.vpc_peers'] == [root_key, 'topology', 'vpc_peers', 'LIST']

    def test_isn_policy_keys(self):
        """Test ISN policy keys."""
        isn = model_keys['ISN']

        assert 'policy' in isn
        assert isn['policy'] == [root_key, 'policy', 'KEY']

        assert 'policy.policies' in isn
        assert isn['policy.policies'] == [root_key, 'policy', 'policies', 'LIST']

        assert 'policy.groups' in isn
        assert isn['policy.groups'] == [root_key, 'policy', 'groups', 'LIST']

        assert 'policy.switches' in isn
        assert isn['policy.switches'] == [root_key, 'policy', 'switches', 'LIST']

    def test_isn_no_global_keys(self):
        """Test that ISN doesn't have global keys."""
        isn = model_keys['ISN']

        # ISN should not have global keys
        assert 'global' not in isn
        assert 'global.dns_servers' not in isn

    def test_isn_no_overlay_keys(self):
        """Test that ISN doesn't have overlay keys."""
        isn = model_keys['ISN']

        # ISN should not have overlay keys
        assert 'overlay' not in isn
        assert 'overlay.vrfs' not in isn


class TestExternalKeys:
    """Test the External fabric type keys."""

    def test_external_topology_keys(self):
        """Test External topology keys."""
        external = model_keys['External']

        assert 'topology' in external
        assert external['topology'] == [root_key, 'topology', 'KEY']

        assert 'topology.edge_connections' in external
        assert external['topology.edge_connections'] == [root_key, 'topology', 'edge_connections', 'LIST']

        assert 'topology.fabric_links' in external
        assert external['topology.fabric_links'] == [root_key, 'topology', 'fabric_links', 'LIST']

        assert 'topology.switches' in external
        assert external['topology.switches'] == [root_key, 'topology', 'switches', 'LIST']

        assert 'topology.switches.freeform' in external
        assert external['topology.switches.freeform'] == [root_key, 'topology', 'switches', 'freeform', 'LIST_INDEX']

        assert 'topology.switches.interfaces' in external
        assert external['topology.switches.interfaces'] == [root_key, 'topology', 'switches', 'interfaces', 'LIST_INDEX']

        assert 'topology.vpc_peers' in external
        assert external['topology.vpc_peers'] == [root_key, 'topology', 'vpc_peers', 'LIST']

    def test_external_policy_keys(self):
        """Test External policy keys."""
        external = model_keys['External']

        assert 'policy' in external
        assert external['policy'] == [root_key, 'policy', 'KEY']

        assert 'policy.policies' in external
        assert external['policy.policies'] == [root_key, 'policy', 'policies', 'LIST']

        assert 'policy.groups' in external
        assert external['policy.groups'] == [root_key, 'policy', 'groups', 'LIST']

        assert 'policy.switches' in external
        assert external['policy.switches'] == [root_key, 'policy', 'switches', 'LIST']

    def test_external_structure_similar_to_isn(self):
        """Test that External structure is similar to ISN."""
        external = model_keys['External']
        isn = model_keys['ISN']

        # External should have the same keys as ISN
        assert set(external.keys()) == set(isn.keys())

        # Values should be identical
        for key in external.keys():
            assert external[key] == isn[key]


class TestMsdKeys:
    """Test the MSD fabric type keys."""

    def test_msd_multisite_keys(self):
        """Test MSD multisite keys."""
        msd = model_keys['MSD']

        assert 'multisite' in msd
        assert msd['multisite'] == [root_key, 'multisite', 'KEY']

        assert 'multisite.child_fabrics' in msd
        assert msd['multisite.child_fabrics'] == [root_key, 'multisite', 'child_fabrics', 'KEY']

    def test_msd_multisite_overlay_keys(self):
        """Test MSD multisite overlay keys."""
        msd = model_keys['MSD']

        assert 'multisite.overlay' in msd
        assert msd['multisite.overlay'] == [root_key, 'multisite', 'overlay', 'KEY']

        assert 'multisite.overlay.vrfs' in msd
        assert msd['multisite.overlay.vrfs'] == [root_key, 'multisite', 'overlay', 'vrfs', 'LIST']

        assert 'multisite.overlay.vrf_attach_groups' in msd
        assert msd['multisite.overlay.vrf_attach_groups'] == [root_key, 'multisite', 'overlay', 'vrf_attach_groups', 'LIST']

        assert 'multisite.overlay.vrf_attach_groups.switches' in msd
        assert msd['multisite.overlay.vrf_attach_groups.switches'] == [root_key, 'multisite', 'overlay', 'vrf_attach_groups', 'switches', 'LIST_INDEX']

        assert 'multisite.overlay.networks' in msd
        assert msd['multisite.overlay.networks'] == [root_key, 'multisite', 'overlay', 'networks', 'LIST']

        assert 'multisite.overlay.network_attach_groups' in msd
        assert msd['multisite.overlay.network_attach_groups'] == [root_key, 'multisite', 'overlay', 'network_attach_groups', 'LIST']

        assert 'multisite.overlay.network_attach_groups.switches' in msd
        assert msd['multisite.overlay.network_attach_groups.switches'] == [root_key, 'multisite', 'overlay', 'network_attach_groups', 'switches', 'LIST_INDEX']

    def test_msd_unique_structure(self):
        """Test that MSD has unique structure compared to other fabric types."""
        msd = model_keys['MSD']

        # MSD should have multisite keys that other fabric types don't have
        assert 'multisite' in msd
        assert 'multisite.child_fabrics' in msd

        # MSD should not have topology or policy keys like other fabric types
        assert 'topology' not in msd
        assert 'policy' not in msd

        # MSD should not have global keys
        assert 'global' not in msd


class TestMcfKeys:
    """Test the MCF fabric type keys."""

    def test_mcf_empty_structure(self):
        """Test that MCF has empty structure."""
        mcf = model_keys['MCF']

        # MCF should be empty dictionary
        assert mcf == {}
        assert len(mcf) == 0

    def test_mcf_no_common_keys(self):
        """Test that MCF doesn't have common keys."""
        mcf = model_keys['MCF']

        # MCF should not have any of the common keys
        assert 'topology' not in mcf
        assert 'policy' not in mcf
        assert 'global' not in mcf
        assert 'overlay' not in mcf
        assert 'multisite' not in mcf


class TestKeyPatterns:
    """Test patterns and consistency in key structures."""

    def test_key_path_structure(self):
        """Test that all key paths follow expected structure."""
        for fabric_type, fabric_keys in model_keys.items():
            for key_name, key_path in fabric_keys.items():
                # All key paths should be lists
                assert isinstance(key_path, list), f"Key path for {fabric_type}.{key_name} should be a list"

                # All key paths should start with root_key
                assert key_path[0] == root_key, f"Key path for {fabric_type}.{key_name} should start with root_key"

                # All key paths should have a type indicator as the last element
                assert key_path[-1] in ['KEY', 'LIST', 'LIST_INDEX'], f"Key path for {fabric_type}.{key_name} should end with a valid type"

    def test_key_type_consistency(self):
        """Test that key types are used consistently."""
        key_types = set()

        for fabric_type, fabric_keys in model_keys.items():
            for key_name, key_path in fabric_keys.items():
                key_types.add(key_path[-1])

        # Should only have these three types
        assert key_types == {'KEY', 'LIST', 'LIST_INDEX'}

    def test_dot_notation_consistency(self):
        """Test that dot notation is used consistently."""
        for fabric_type, fabric_keys in model_keys.items():
            for key_name, key_path in fabric_keys.items():
                # Count dots in key_name
                dot_count = key_name.count('.')

                # Key path length should be dot_count + 2 (root_key + type indicator)
                expected_length = dot_count + 3  # root_key + path_parts + type
                assert len(key_path) == expected_length, f"Key path length mismatch for {fabric_type}.{key_name}"

    def test_common_topology_structure(self):
        """Test that topology structures are consistent across fabric types."""
        topology_fabric_types = ['VXLAN_EVPN', 'ISN', 'External']

        common_topology_keys = [
            'topology.edge_connections',
            'topology.fabric_links',
            'topology.switches',
            'topology.switches.freeform',
            'topology.switches.interfaces',
            'topology.vpc_peers'
        ]

        for fabric_type in topology_fabric_types:
            fabric_keys = model_keys[fabric_type]

            for topology_key in common_topology_keys:
                assert topology_key in fabric_keys, f"{fabric_type} should have {topology_key}"

    def test_common_policy_structure(self):
        """Test that policy structures are consistent across fabric types."""
        policy_fabric_types = ['VXLAN_EVPN', 'ISN', 'External']

        common_policy_keys = [
            'policy.policies',
            'policy.groups',
            'policy.switches'
        ]

        for fabric_type in policy_fabric_types:
            fabric_keys = model_keys[fabric_type]

            for policy_key in common_policy_keys:
                assert policy_key in fabric_keys, f"{fabric_type} should have {policy_key}"

    def test_list_index_usage(self):
        """Test that LIST_INDEX is used appropriately."""
        list_index_keys = []

        for fabric_type, fabric_keys in model_keys.items():
            for key_name, key_path in fabric_keys.items():
                if key_path[-1] == 'LIST_INDEX':
                    list_index_keys.append(f"{fabric_type}.{key_name}")

        # LIST_INDEX should be used for nested list items
        expected_patterns = [
            'switches.freeform',
            'switches.interfaces',
            'vrf_attach_groups.switches',
            'network_attach_groups.switches'
        ]

        for list_index_key in list_index_keys:
            # Check that the key contains one of the expected patterns
            assert any(pattern in list_index_key for pattern in expected_patterns), \
                f"LIST_INDEX key {list_index_key} should match expected patterns"


class TestDataModelKeysIntegration:
    """Integration tests for data model keys."""

    def test_key_path_reconstruction(self):
        """Test that key paths can be used to reconstruct data model paths."""
        # Test a few key paths
        test_cases = [
            ('VXLAN_EVPN', 'global.dns_servers', ['vxlan', 'global', 'dns_servers']),
            ('VXLAN_EVPN', 'topology.switches', ['vxlan', 'topology', 'switches']),
            ('MSD', 'multisite.overlay.vrfs', ['vxlan', 'multisite', 'overlay', 'vrfs']),
        ]

        for fabric_type, key_name, expected_path in test_cases:
            if key_name in model_keys[fabric_type]:
                key_path = model_keys[fabric_type][key_name]
                actual_path = key_path[:-1]  # Remove the type indicator
                assert actual_path == expected_path, \
                    f"Key path for {fabric_type}.{key_name} should reconstruct to {expected_path}"

    def test_fabric_type_coverage(self):
        """Test that all fabric types have appropriate coverage."""
        fabric_coverage = {}

        for fabric_type, fabric_keys in model_keys.items():
            fabric_coverage[fabric_type] = len(fabric_keys)

        # VXLAN_EVPN should have the most keys (it's the most comprehensive)
        assert fabric_coverage['VXLAN_EVPN'] > 0

        # MCF should have no keys (it's empty)
        assert fabric_coverage['MCF'] == 0

        # MSD should have multisite-specific keys
        assert fabric_coverage['MSD'] > 0

        # ISN and External should have similar coverage
        assert fabric_coverage['ISN'] > 0
        assert fabric_coverage['External'] > 0

    def test_key_uniqueness_within_fabric_type(self):
        """Test that keys are unique within each fabric type."""
        for fabric_type, fabric_keys in model_keys.items():
            key_names = list(fabric_keys.keys())
            unique_key_names = list(set(key_names))

            assert len(key_names) == len(unique_key_names), \
                f"Duplicate keys found in {fabric_type}: {set([x for x in key_names if key_names.count(x) > 1])}"

    def test_realistic_key_usage_patterns(self):
        """Test realistic patterns for how keys might be used."""
        # Test accessing nested data using key paths
        mock_data = {
            'vxlan': {
                'global': {
                    'dns_servers': ['8.8.8.8', '8.8.4.4']
                },
                'topology': {
                    'switches': [
                        {'name': 'leaf-01', 'role': 'leaf'}
                    ]
                }
            }
        }

        # Test VXLAN_EVPN global.dns_servers key
        key_path = model_keys['VXLAN_EVPN']['global.dns_servers']
        path_without_type = key_path[:-1]  # Remove 'LIST'

        # Navigate through the mock data
        current_data = mock_data
        for path_part in path_without_type:
            current_data = current_data[path_part]

        assert current_data == ['8.8.8.8', '8.8.4.4']

        # Test topology.switches key
        key_path = model_keys['VXLAN_EVPN']['topology.switches']
        path_without_type = key_path[:-1]  # Remove 'LIST'

        current_data = mock_data
        for path_part in path_without_type:
            current_data = current_data[path_part]

        assert current_data == [{'name': 'leaf-01', 'role': 'leaf'}]


if __name__ == "__main__":
    pytest.main([__file__])

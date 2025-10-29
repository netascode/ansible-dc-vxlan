class Rule:
    id = "311"
    description = "Validate ToR pairing configuration and verify no network attachments on ToRs being removed"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        """
        Comprehensive ToR pairing validation:
        1. Validate ToR pairing entries before they are processed by prepare plugins
        2. Verify that ToRs being removed do not have networks attached
        
        This catches configuration errors early in the validation phase.
        """
        results = []
        
        # Get topology
        topology_keys = ['vxlan', 'topology']
        dm_check = cls.data_model_key_check(data_model, topology_keys)
        if 'topology' not in dm_check['keys_data']:
            return results
        
        topology = data_model['vxlan']['topology']
        
        # Get tor_peers
        if 'tor_peers' not in topology or not topology['tor_peers']:
            return results
        
        tor_peers = topology['tor_peers']
        switches = topology.get('switches', [])
        vpc_peers = topology.get('vpc_peers', [])
        
        # Build switch lookup map
        switch_map = {}
        switch_names = set()
        for sw in switches:
            if 'name' in sw:
                switch_map[sw['name']] = sw
                switch_names.add(sw['name'])
        
        # Build VPC domain lookup map
        vpc_domain_map = {}
        for vpc_pair in vpc_peers:
            peer1 = vpc_pair.get('peer1')
            peer2 = vpc_pair.get('peer2')
            domain_id = vpc_pair.get('domain_id')
            if peer1 and peer2 and domain_id:
                # Store both directions for easy lookup
                vpc_domain_map[(peer1, peer2)] = domain_id
                vpc_domain_map[(peer2, peer1)] = domain_id
        
        # Collect all ToR switch names referenced in tor_peers
        tor_switch_names = set()
        
        # Validate each tor_peers entry
        for idx, peer in enumerate(tor_peers):
            entry_label = f"vxlan.topology.tor_peers[{idx}]"
            
            # Handle both dict and string formats (backward compatibility)
            leaf1_name = cls._extract_name(peer.get('parent_leaf1'))
            leaf2_name = cls._extract_name(peer.get('parent_leaf2'))
            tor1_name = cls._extract_name(peer.get('tor1'))
            tor2_name = cls._extract_name(peer.get('tor2'))
            
            # Track ToR names
            if tor1_name:
                tor_switch_names.add(tor1_name)
            if tor2_name:
                tor_switch_names.add(tor2_name)
            
            # Basic required field check
            if not leaf1_name or not tor1_name:
                results.append(f"{entry_label}: 'parent_leaf1' and 'tor1' are required")
                continue
            
            # Determine scenario
            scenario = cls._detect_scenario(leaf1_name, leaf2_name, tor1_name, tor2_name)
            
            # Scenario-specific validation
            if scenario == 'vpc_to_vpc':
                # Validate: leafs must be VPC paired
                if not cls._find_vpc_domain(leaf1_name, leaf2_name, vpc_domain_map):
                    results.append(
                        f"{entry_label}: vpc-to-vpc scenario requires leafs '{leaf1_name}' and '{leaf2_name}' "
                        f"to be VPC paired in vxlan.topology.vpc_peers"
                    )
                # Validate: tors must be VPC paired
                if not cls._find_vpc_domain(tor1_name, tor2_name, vpc_domain_map):
                    results.append(
                        f"{entry_label}: vpc-to-vpc scenario requires TORs '{tor1_name}' and '{tor2_name}' "
                        f"to be VPC paired in vxlan.topology.vpc_peers"
                    )
                # Validate: all 4 switches must exist with correct roles
                cls._validate_switch_role(leaf1_name, 'leaf', switch_map, results, entry_label)
                cls._validate_switch_role(leaf2_name, 'leaf', switch_map, results, entry_label)
                cls._validate_switch_role(tor1_name, 'tor', switch_map, results, entry_label)
                cls._validate_switch_role(tor2_name, 'tor', switch_map, results, entry_label)
                
            elif scenario == 'vpc_to_standalone':
                # Validate: leafs must be VPC paired
                if not cls._find_vpc_domain(leaf1_name, leaf2_name, vpc_domain_map):
                    results.append(
                        f"{entry_label}: vpc-to-standalone scenario requires leafs '{leaf1_name}' and '{leaf2_name}' "
                        f"to be VPC paired in vxlan.topology.vpc_peers"
                    )
                # Validate: switches must exist with correct roles
                cls._validate_switch_role(leaf1_name, 'leaf', switch_map, results, entry_label)
                cls._validate_switch_role(leaf2_name, 'leaf', switch_map, results, entry_label)
                cls._validate_switch_role(tor1_name, 'tor', switch_map, results, entry_label)
                
            elif scenario == 'standalone_to_standalone':
                # Validate: switches must exist with correct roles
                cls._validate_switch_role(leaf1_name, 'leaf', switch_map, results, entry_label)
                cls._validate_switch_role(tor1_name, 'tor', switch_map, results, entry_label)
                
            else:
                results.append(
                    f"{entry_label}: Invalid ToR pairing scenario. "
                    f"Supported: vpc-to-vpc (2 leafs + 2 TORs), vpc-to-standalone (2 leafs + 1 TOR), "
                    f"standalone-to-standalone (1 leaf + 1 TOR). "
                    f"Unsupported: standalone leaf with VPC TORs"
                )
        
        # Now check for network attachments on ToRs being removed
        # Identify ToRs that are being removed (in tor_peers but NOT in switches inventory)
        removed_tors = tor_switch_names - switch_names
        
        # If no ToRs are being removed, skip network attachment validation
        if removed_tors:
            network_attachment_errors = cls._validate_network_attachments(data_model, removed_tors)
            results.extend(network_attachment_errors)
        
        return results
    
    @classmethod
    def _validate_network_attachments(cls, data_model, removed_tors):
        """
        Check if any networks are attached to ToR switches that are being removed.
        """
        results = []
        
        # Check for network attachments to removed ToRs
        # Check both overlay.networks and multisite.overlay.networks
        networks_to_check = []
        
        # Standard overlay path
        overlay_networks_keys = ['vxlan', 'overlay', 'networks']
        dm_check = cls.data_model_key_check(data_model, overlay_networks_keys)
        if 'networks' in dm_check['keys_data']:
            networks_to_check.extend(data_model['vxlan']['overlay']['networks'])
        
        # Multisite overlay path
        multisite_networks_keys = ['vxlan', 'multisite', 'overlay', 'networks']
        dm_check = cls.data_model_key_check(data_model, multisite_networks_keys)
        if 'networks' in dm_check['keys_data']:
            networks_to_check.extend(data_model['vxlan']['multisite']['overlay']['networks'])
        
        # Check network attach groups
        network_attach_groups = []
        
        # Standard overlay attach groups
        overlay_groups_keys = ['vxlan', 'overlay', 'network_attach_groups']
        dm_check = cls.data_model_key_check(data_model, overlay_groups_keys)
        if 'network_attach_groups' in dm_check['keys_data']:
            network_attach_groups.extend(data_model['vxlan']['overlay']['network_attach_groups'])
        
        # Multisite overlay attach groups
        multisite_groups_keys = ['vxlan', 'multisite', 'overlay', 'network_attach_groups']
        dm_check = cls.data_model_key_check(data_model, multisite_groups_keys)
        if 'network_attach_groups' in dm_check['keys_data']:
            network_attach_groups.extend(data_model['vxlan']['multisite']['overlay']['network_attach_groups'])
        
        # Build a map of network_attach_group name to the networks using it
        group_to_networks = {}
        for network in networks_to_check:
            if 'network_attach_group' in network:
                group_name = network['network_attach_group']
                if group_name not in group_to_networks:
                    group_to_networks[group_name] = []
                group_to_networks[group_name].append(network['name'])
        
        # Check each attach group for ToR attachments
        for group in network_attach_groups:
            group_name = group.get('name')
            if not group_name:
                continue
            
            # Get switches in this group
            group_switches = group.get('switches', [])
            
            for switch_entry in group_switches:
                hostname = switch_entry.get('hostname')
                
                # Check if this hostname is a ToR being removed
                if hostname in removed_tors:
                    # Get the networks using this attach group
                    affected_networks = group_to_networks.get(group_name, [])
                    for network_name in affected_networks:
                        results.append(
                            f"Network '{network_name}' is attached to ToR switch '{hostname}' "
                            f"which is being removed. Remove network attachment from "
                            f"vxlan.overlay.network_attach_groups.{group_name} before removing the ToR pairing."
                        )
                
                # Also check tors within the switch entry
                tors = switch_entry.get('tors', [])
                for tor_entry in tors:
                    tor_hostname = tor_entry.get('hostname')
                    if tor_hostname in removed_tors:
                        affected_networks = group_to_networks.get(group_name, [])
                        for network_name in affected_networks:
                            results.append(
                                f"Network '{network_name}' has ports attached to ToR switch '{tor_hostname}' "
                                f"which is being removed. Remove network attachment from "
                                f"vxlan.overlay.network_attach_groups.{group_name}.switches.{hostname}.tors "
                                f"before removing the ToR pairing."
                            )
        
        return results
    
    @classmethod
    def _extract_name(cls, value):
        """Extract switch name from dict or string."""
        if not value:
            return None
        return value.get('name') if isinstance(value, dict) else value
    
    @classmethod
    def _detect_scenario(cls, leaf1, leaf2, tor1, tor2):
        """Detect ToR pairing scenario."""
        if leaf2 and tor2:
            return 'vpc_to_vpc'
        elif leaf2 and not tor2:
            return 'vpc_to_standalone'
        elif not leaf2 and not tor2:
            return 'standalone_to_standalone'
        else:
            return 'invalid'  # standalone leaf + vpc tor
    
    @classmethod
    def _find_vpc_domain(cls, switch1, switch2, vpc_domain_map):
        """Check if two switches form a VPC pair."""
        return vpc_domain_map.get((switch1, switch2)) is not None
    
    @classmethod
    def _validate_switch_role(cls, switch_name, expected_role, switch_map, results, entry_label):
        """Validate switch exists and has correct role."""
        if switch_name not in switch_map:
            results.append(
                f"{entry_label}: Switch '{switch_name}' not found in vxlan.topology.switches"
            )
            return
        
        switch = switch_map[switch_name]
        if switch.get('role') != expected_role:
            results.append(
                f"{entry_label}: Switch '{switch_name}' must have role '{expected_role}', "
                f"found '{switch.get('role')}'"
            )
        
        if not switch.get('serial_number'):
            results.append(
                f"{entry_label}: Switch '{switch_name}' must have serial_number defined"
            )
    
    @classmethod
    def data_model_key_check(cls, tested_object, keys):
        """
        Navigate through nested dictionary keys and track which keys exist and contain data.
        """
        dm_key_dict = {'keys_found': [], 'keys_not_found': [], 'keys_data': [], 'keys_no_data': []}
        for key in keys:
            if tested_object and key in tested_object:
                dm_key_dict['keys_found'].append(key)
                tested_object = tested_object[key]
                if tested_object:
                    dm_key_dict['keys_data'].append(key)
                else:
                    dm_key_dict['keys_no_data'].append(key)
            else:
                dm_key_dict['keys_not_found'].append(key)
        return dm_key_dict

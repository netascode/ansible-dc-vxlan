class Rule:
    id = "311"
    description = "Validate ToR pairing configuration (scenarios, VPC requirements, switch roles)"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        """
        Validate ToR pairing configuration before it's processed by prepare plugins.
        
        Checks:
        1. Required fields (parent_leaf1, tor1) are present
        2. Scenario detection (vpc-to-vpc, vpc-to-standalone, standalone-to-standalone)
        3. VPC requirements (leafs/ToRs must be VPC paired per scenario)
        4. Switch existence and role validation
        5. Serial number presence
        
        6. Check if its preprobisioning then failed
        
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
                # Validate: all 4 switches must exist with correct roles - only leaf and tor roles are supported. BGW or BL roles are invalid.
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

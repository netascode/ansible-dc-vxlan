class Rule:
    id = "312"
    description = "Verify ToR pairing configuration is valid and complete"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        """
        Validate ToR pairing entries before they are processed by prepare plugins.
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
        for sw in switches:
            if 'name' in sw:
                switch_map[sw['name']] = sw
        
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
        
        # Track pairing IDs for duplicate detection
        pairing_ids = set()
        
        # Validate each tor_peers entry
        for idx, peer in enumerate(tor_peers):
            entry_label = f"vxlan.topology.tor_peers[{idx}]"
            
            # Extract names from the peer entry
            parent_leaf1 = peer.get('parent_leaf1')
            parent_leaf2 = peer.get('parent_leaf2')
            tor1 = peer.get('tor1')
            tor2 = peer.get('tor2')
            
            # Check required fields
            if not parent_leaf1:
                results.append(f"{entry_label}: 'parent_leaf1' is required")
                continue
            if not tor1:
                results.append(f"{entry_label}: 'tor1' is required")
                continue
            
            # Handle both dict and string formats for switch references
            leaf1_name = parent_leaf1.get('name') if isinstance(parent_leaf1, dict) else parent_leaf1
            leaf2_name = parent_leaf2.get('name') if isinstance(parent_leaf2, dict) and parent_leaf2 else None
            tor1_name = tor1.get('name') if isinstance(tor1, dict) else tor1
            tor2_name = tor2.get('name') if isinstance(tor2, dict) and tor2 else None
            
            # Validate leaf1 exists and has correct role
            if leaf1_name not in switch_map:
                results.append(
                    f"{entry_label}: parent_leaf1 switch '{leaf1_name}' not found in vxlan.topology.switches"
                )
            else:
                leaf1_sw = switch_map[leaf1_name]
                if leaf1_sw.get('role') != 'leaf':
                    results.append(
                        f"{entry_label}: parent_leaf1 switch '{leaf1_name}' must have role 'leaf', "
                        f"current role is '{leaf1_sw.get('role')}'"
                    )
                if not leaf1_sw.get('serial_number'):
                    results.append(
                        f"{entry_label}: parent_leaf1 switch '{leaf1_name}' must have a serial_number defined"
                    )
            
            # Validate leaf2 if provided
            if leaf2_name:
                if leaf2_name not in switch_map:
                    results.append(
                        f"{entry_label}: parent_leaf2 switch '{leaf2_name}' not found in vxlan.topology.switches"
                    )
                else:
                    leaf2_sw = switch_map[leaf2_name]
                    if leaf2_sw.get('role') != 'leaf':
                        results.append(
                            f"{entry_label}: parent_leaf2 switch '{leaf2_name}' must have role 'leaf', "
                            f"current role is '{leaf2_sw.get('role')}'"
                        )
                    if not leaf2_sw.get('serial_number'):
                        results.append(
                            f"{entry_label}: parent_leaf2 switch '{leaf2_name}' must have a serial_number defined"
                        )
            
            # Validate tor1 exists and has correct role
            if tor1_name not in switch_map:
                results.append(
                    f"{entry_label}: tor1 switch '{tor1_name}' not found in vxlan.topology.switches"
                )
            else:
                tor1_sw = switch_map[tor1_name]
                if tor1_sw.get('role') != 'tor':
                    results.append(
                        f"{entry_label}: tor1 switch '{tor1_name}' must have role 'tor', "
                        f"current role is '{tor1_sw.get('role')}'"
                    )
                if not tor1_sw.get('serial_number'):
                    results.append(
                        f"{entry_label}: tor1 switch '{tor1_name}' must have a serial_number defined"
                    )
            
            # Validate tor2 if provided
            if tor2_name:
                if tor2_name not in switch_map:
                    results.append(
                        f"{entry_label}: tor2 switch '{tor2_name}' not found in vxlan.topology.switches"
                    )
                else:
                    tor2_sw = switch_map[tor2_name]
                    if tor2_sw.get('role') != 'tor':
                        results.append(
                            f"{entry_label}: tor2 switch '{tor2_name}' must have role 'tor', "
                            f"current role is '{tor2_sw.get('role')}'"
                        )
                    if not tor2_sw.get('serial_number'):
                        results.append(
                            f"{entry_label}: tor2 switch '{tor2_name}' must have a serial_number defined"
                        )
            
            # Validate tor_vpc_peer consistency
            tor_vpc_peer = peer.get('tor_vpc_peer', peer.get('vpc_peer', False))
            
            if tor_vpc_peer and not tor2:
                results.append(
                    f"{entry_label}: tor_vpc_peer is true but tor2 is not provided. "
                    f"ToR vPC requires both tor1 and tor2."
                )
            elif tor2 and not tor_vpc_peer:
                results.append(
                    f"{entry_label}: tor2 is defined but tor_vpc_peer is false. "
                    f"Set tor_vpc_peer to true when defining a ToR vPC pair."
                )
            
            # Validate VPC domain IDs
            leaf_vpc_id = peer.get('leaf_vpc_id')
            tor_vpc_id = peer.get('tor_vpc_id')
            
            # Check if leaf VPC domain is needed
            if leaf2_name:
                # Leaf vPC scenario - need domain ID
                if not leaf_vpc_id:
                    # Try to find it from vpc_peers
                    if leaf1_name and leaf2_name:
                        domain_id = vpc_domain_map.get((leaf1_name, leaf2_name))
                        if not domain_id:
                            results.append(
                                f"{entry_label}: parent_leaf1 '{leaf1_name}' and parent_leaf2 '{leaf2_name}' "
                                f"form a vPC but no leaf_vpc_id is defined and no matching entry found in "
                                f"vxlan.topology.vpc_peers"
                            )
                else:
                    # Verify leaf_vpc_id is an integer
                    if not isinstance(leaf_vpc_id, int):
                        results.append(
                            f"{entry_label}: leaf_vpc_id must be an integer, got {type(leaf_vpc_id).__name__}"
                        )
            
            # Check if tor VPC domain is needed
            if tor_vpc_peer and tor2_name:
                if not tor_vpc_id:
                    # Try to find it from vpc_peers
                    if tor1_name and tor2_name:
                        domain_id = vpc_domain_map.get((tor1_name, tor2_name))
                        if not domain_id:
                            results.append(
                                f"{entry_label}: tor1 '{tor1_name}' and tor2 '{tor2_name}' "
                                f"form a vPC but no tor_vpc_id is defined and no matching entry found in "
                                f"vxlan.topology.vpc_peers"
                            )
                else:
                    # Verify tor_vpc_id is an integer
                    if not isinstance(tor_vpc_id, int):
                        results.append(
                            f"{entry_label}: tor_vpc_id must be an integer, got {type(tor_vpc_id).__name__}"
                        )
            
            # Validate supported scenarios
            # Scenario: tor vPC with standalone leaf is NOT supported
            if tor_vpc_peer and not leaf2_name:
                results.append(
                    f"{entry_label}: Unsupported ToR pairing scenario - ToR vPC with standalone leaf. "
                    f"ToR vPC (tor1='{tor1_name}', tor2='{tor2_name}') requires a leaf vPC "
                    f"(both parent_leaf1 and parent_leaf2 must be defined)."
                )
            
            # Validate unique pairing ID
            pairing_id = peer.get('pairing_id')
            if not pairing_id and leaf1_name and tor1_name:
                # Generate default pairing_id
                pairing_id = f"{leaf1_name}-{tor1_name}"
            
            if pairing_id:
                if pairing_id in pairing_ids:
                    results.append(
                        f"{entry_label}: Duplicate pairing_id '{pairing_id}'. "
                        f"Each ToR pairing must have a unique pairing_id."
                    )
                else:
                    pairing_ids.add(pairing_id)
        
        return results

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

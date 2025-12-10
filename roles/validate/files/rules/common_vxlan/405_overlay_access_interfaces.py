"""
Validation Rules scenarios:
1. For each interface under vxlan.topology.switches.[switch].interfaces that is configured as "mode: access"
   - If the interface has "access_vlan" defined:
     it cannot be referenced in vxlan.overlay.networks.network_attach_groups sections
   - If the interface doesn't have "access_vlan" defined:
     it can be referenced at maximum one time in vxlan.overlay.networks.network_attach_groups sections
2. Network attach groups containing access ports cannot be referenced by multiple networks
   (checked at vxlan.overlay.networks[].network_attach_group and vxlan.multisite.overlay.networks[].network_attach_group)
"""


class Rule:
    """
    Class 405 - Verify access interface VLAN assignments and network attach group references
    """

    id = "405"
    description = "Verify access interface VLAN assignments and network attach group references"
    severity = "HIGH"
    results = []

    @classmethod
    def match(cls, data_model):
        """
        Function used by nac-validate
        """
        cls.results = []

        # Get switches from topology
        switches_keys = ['vxlan', 'topology', 'switches']
        check = cls.data_model_key_check(data_model, switches_keys)
        if 'switches' not in check['keys_data']:
            # No switches defined, nothing to validate
            return cls.results

        switches = cls.safeget(data_model, switches_keys)
        if not switches:
            return cls.results

        # Build a map of access interfaces from topology
        access_interfaces_map = cls.build_access_interfaces_map(switches)

        # Try multiple possible overlay locations and collect all network attach group references
        # Support: vxlan.overlay and vxlan.multisite.overlay
        overlay_paths = [
            ['vxlan', 'overlay'],
            ['vxlan', 'multisite', 'overlay']
        ]
        
        all_interface_references = {}
        
        for overlay_path in overlay_paths:
            # Check if this overlay path exists
            check = cls.data_model_key_check(data_model, overlay_path)
            if overlay_path[-1] not in check['keys_data']:
                # This overlay path doesn't exist, try next one
                continue
            
            # Get network attach groups from this overlay location
            network_attach_groups_keys = overlay_path + ['network_attach_groups']
            check = cls.data_model_key_check(data_model, network_attach_groups_keys)
            
            if 'network_attach_groups' in check['keys_data']:
                network_attach_groups = cls.safeget(data_model, network_attach_groups_keys)
                
                if network_attach_groups:
                    # Build interface references from this overlay location
                    interface_references = cls.build_network_attach_references(network_attach_groups)
                    
                    # Merge with all collected references
                    for key, group_names in interface_references.items():
                        if key not in all_interface_references:
                            all_interface_references[key] = []
                        all_interface_references[key].extend(group_names)
        
        # If no network attach groups found in any location, nothing to validate
        if not all_interface_references:
            return cls.results

        # Build a map of interface references in network attach groups
        interface_references = all_interface_references

        # Validate access interfaces against network attach groups
        cls.validate_access_interface_references(
            access_interfaces_map,
            interface_references
        )

        # Validate that network attach groups with access ports are not referenced by multiple networks
        for overlay_path in overlay_paths:
            # Check if this overlay path exists
            check = cls.data_model_key_check(data_model, overlay_path)
            if overlay_path[-1] not in check['keys_data']:
                continue
            
            # Get networks and network attach groups from this overlay location
            networks_keys = overlay_path + ['networks']
            network_attach_groups_keys = overlay_path + ['network_attach_groups']
            
            check_networks = cls.data_model_key_check(data_model, networks_keys)
            check_nag = cls.data_model_key_check(data_model, network_attach_groups_keys)
            
            if 'networks' in check_networks['keys_data'] and 'network_attach_groups' in check_nag['keys_data']:
                networks = cls.safeget(data_model, networks_keys)
                network_attach_groups = cls.safeget(data_model, network_attach_groups_keys)
                
                if networks and network_attach_groups:
                    cls.validate_network_attach_group_reuse(
                        networks,
                        network_attach_groups,
                        all_interface_references
                    )

        return cls.results

    @classmethod
    def build_access_interfaces_map(cls, switches):
        """
        Build a map of access interfaces with their access_vlan status
        Returns: dict with key=(hostname, interface_name), value={'has_access_vlan': bool, 'hostname': str, 'interface': str}
        """
        access_interfaces = {}

        for switch in switches:
            hostname = switch.get('name')
            if not hostname:
                continue

            interfaces = switch.get('interfaces', [])
            for interface in interfaces:
                interface_name = interface.get('name')
                interface_mode = interface.get('mode')

                # Only process access mode interfaces
                if interface_mode == 'access' and interface_name:
                    key = (hostname, interface_name)
                    has_access_vlan = 'access_vlan' in interface and interface.get('access_vlan') is not None

                    access_interfaces[key] = {
                        'has_access_vlan': has_access_vlan,
                        'hostname': hostname,
                        'interface': interface_name
                    }

        return access_interfaces

    @classmethod
    def build_network_attach_references(cls, network_attach_groups):
        """
        Build a map of interface references in network attach groups
        Returns: dict with key=(hostname, interface_name), value=[list of network attach group names]
        """
        interface_references = {}

        for attach_group in network_attach_groups:
            group_name = attach_group.get('name')
            if not group_name:
                continue

            # Get switches from the attach group
            attach_switches = attach_group.get('switches', [])

            for attach_switch in attach_switches:
                hostname = attach_switch.get('hostname')
                if not hostname:
                    continue

                # Get ports from the attach switch
                # Ports can be either a list of strings or a list of objects with 'name' attribute
                ports = attach_switch.get('ports', [])
                for port in ports:
                    # Handle both string format and object format
                    if isinstance(port, str):
                        interface_name = port
                    elif isinstance(port, dict):
                        interface_name = port.get('name')
                    else:
                        continue
                    
                    if not interface_name:
                        continue

                    key = (hostname, interface_name)
                    if key not in interface_references:
                        interface_references[key] = []
                    interface_references[key].append(group_name)
                
                # Also check ports under tors (for TOR/leaf switch configurations)
                tors = attach_switch.get('tors', [])
                for tor in tors:
                    tor_hostname = tor.get('hostname')
                    if not tor_hostname:
                        continue
                    
                    tor_ports = tor.get('ports', [])
                    for port in tor_ports:
                        # Handle both string format and object format
                        if isinstance(port, str):
                            interface_name = port
                        elif isinstance(port, dict):
                            interface_name = port.get('name')
                        else:
                            continue
                        
                        if not interface_name:
                            continue

                        # Use (leaf_hostname, tor_hostname, interface_name) as key for TOR ports
                        # since the same TOR can be attached to different leaf switches
                        key = (hostname, tor_hostname, interface_name)
                        if key not in interface_references:
                            interface_references[key] = []
                        interface_references[key].append(group_name)

        return interface_references

    @classmethod
    def validate_access_interface_references(cls, access_interfaces_map, interface_references):
        """
        Validate access interface references against network attach groups
        """
        # First, validate direct switch port references (2-tuple keys)
        for key, interface_info in access_interfaces_map.items():
            hostname = interface_info['hostname']
            interface_name = interface_info['interface']
            has_access_vlan = interface_info['has_access_vlan']

            # Check if this interface is referenced in network attach groups as a direct port
            referenced_networks = interface_references.get(key, [])
            reference_count = len(referenced_networks)

            if has_access_vlan:
                # Interface has access_vlan defined - it cannot be referenced in network attach groups
                if reference_count > 0:
                    network_list = ', '.join(referenced_networks)
                    cls.results.append(
                        f"Access interface '{interface_name}' on switch '{hostname}' has 'access_vlan' defined "
                        f"and cannot be referenced in network_attach_groups. "
                        f"Found in networks: {network_list}. "
                        f"Please remove 'access_vlan' from the interface definition or remove the interface "
                        f"from the network_attach_groups."
                    )
            else:
                # Interface doesn't have access_vlan - it can only be referenced once
                if reference_count > 1:
                    network_list = ', '.join(referenced_networks)
                    cls.results.append(
                        f"Access interface '{interface_name}' on switch '{hostname}' is referenced {reference_count} times "
                        f"in network_attach_groups (networks: {network_list}). "
                        f"Access interfaces without 'access_vlan' defined can only belong to a single VLAN "
                        f"and must be referenced at most once in network_attach_groups."
                    )

        # Second, validate TOR port references (3-tuple keys)
        # Group TOR references by (leaf, tor, interface) and check for duplicates per leaf
        for ref_key, group_names in interface_references.items():
            # Skip 2-tuple keys (already validated above)
            if len(ref_key) != 3:
                continue
            
            leaf_hostname, tor_hostname, interface_name = ref_key
            
            # Check if this TOR interface exists in access_interfaces_map
            tor_key = (tor_hostname, interface_name)
            if tor_key not in access_interfaces_map:
                # Interface not defined in topology, skip validation
                continue
            
            interface_info = access_interfaces_map[tor_key]
            has_access_vlan = interface_info['has_access_vlan']
            
            reference_count = len(group_names)
            
            if has_access_vlan:
                # Interface has access_vlan defined - it cannot be referenced in network attach groups
                if reference_count > 0:
                    network_list = ', '.join(group_names)
                    cls.results.append(
                        f"Access interface '{interface_name}' on TOR '{tor_hostname}' (attached to '{leaf_hostname}') "
                        f"has 'access_vlan' defined and cannot be referenced in network_attach_groups. "
                        f"Found in networks: {network_list}. "
                        f"Please remove 'access_vlan' from the interface definition or remove the interface "
                        f"from the network_attach_groups."
                    )
            else:
                # Interface doesn't have access_vlan - it can only be referenced once per leaf
                if reference_count > 1:
                    network_list = ', '.join(group_names)
                    cls.results.append(
                        f"Access interface '{interface_name}' on TOR '{tor_hostname}' (attached to '{leaf_hostname}') "
                        f"is referenced {reference_count} times in network_attach_groups (networks: {network_list}). "
                        f"Access interfaces without 'access_vlan' defined can only belong to a single VLAN "
                        f"and must be referenced at most once in network_attach_groups."
                    )

    @classmethod
    def validate_network_attach_group_reuse(cls, networks, network_attach_groups, interface_references):
        """
        Validate that network attach groups containing access ports are not referenced by multiple networks
        """
        # Build a map of network attach group names that contain access interfaces
        nag_with_access_ports = set()
        
        for ref_key in interface_references.keys():
            # Get the network attach group names that reference this interface
            group_names = interface_references[ref_key]
            for group_name in group_names:
                nag_with_access_ports.add(group_name)
        
        # Build a map of network attach groups to networks that reference them
        nag_to_networks = {}
        
        for network in networks:
            network_name = network.get('name')
            network_attach_group = network.get('network_attach_group')
            
            if not network_name or not network_attach_group:
                continue
            
            # Only track network attach groups that contain access ports
            if network_attach_group in nag_with_access_ports:
                if network_attach_group not in nag_to_networks:
                    nag_to_networks[network_attach_group] = []
                nag_to_networks[network_attach_group].append(network_name)
        
        # Check for network attach groups referenced by multiple networks
        for nag_name, network_names in nag_to_networks.items():
            if len(network_names) > 1:
                network_list = ', '.join(network_names)
                cls.results.append(
                    f"Network attach group '{nag_name}' contains access ports and is referenced by multiple networks: {network_list}. "
                    f"Network attach groups with access ports can only be attached to a single network."
                )

    @classmethod
    def data_model_key_check(cls, tested_object, keys):
        """
        Utility function to check if keys exist in nested dictionary
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

    @classmethod
    def safeget(cls, dict, keys):
        """
        Utility function to safely get nested dictionary values
        """
        for key in keys:
            if dict is None:
                return None
            if key in dict:
                dict = dict[key]
            else:
                return None

        return dict

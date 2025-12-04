"""
Validation Rules scenarios:
1. For each interface under vxlan.topology.switches.[switch].interfaces that is configured as "mode: access"
   - If the interface has "access_vlan" defined:
     it cannot be referenced in vxlan.overlay.networks.network_attach_groups sections
   - If the interface doesn't have "access_vlan" defined:
     it can be referenced at maximum one time in vxlan.overlay.networks.network_attach_groups sections
"""


class Rule:
    """
    Class 404 - Verify access interface VLAN assignments and network attach group references
    """

    id = "404"
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

        # Determine overlay key (overlay or overlay_services for backward compatibility)
        overlay_key = 'overlay'
        check = cls.data_model_key_check(data_model, ['vxlan', overlay_key])
        if overlay_key in check['keys_not_found'] or overlay_key in check['keys_no_data']:
            overlay_key = 'overlay_services'

        # Get networks and network attach groups
        networks_keys = ['vxlan', overlay_key, 'networks']
        check = cls.data_model_key_check(data_model, networks_keys)
        if 'networks' not in check['keys_data']:
            # No networks defined, nothing to validate
            return cls.results

        networks = cls.safeget(data_model, networks_keys)
        if not networks:
            return cls.results

        # Build a map of access interfaces from topology
        access_interfaces_map = cls.build_access_interfaces_map(switches)

        # Build a map of interface references in network attach groups
        interface_references = cls.build_network_attach_references(networks)

        # Validate access interfaces against network attach groups
        cls.validate_access_interface_references(
            access_interfaces_map,
            interface_references
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
    def build_network_attach_references(cls, networks):
        """
        Build a map of interface references in network attach groups
        Returns: dict with key=(hostname, interface_name), value=[list of network names]
        """
        interface_references = {}

        for network in networks:
            network_name = network.get('name')
            if not network_name:
                continue

            network_attach_group = network.get('network_attach_group')
            if not network_attach_group:
                continue

            # Get the attach group switches
            attach_group_keys = ['switches']
            attach_switches = network.get('network_attach_group', {}).get('switches', [])

            for attach_switch in attach_switches:
                hostname = attach_switch.get('hostname')
                if not hostname:
                    continue

                # Get ports from the attach switch
                ports = attach_switch.get('ports', [])
                for port in ports:
                    interface_name = port.get('name')
                    if not interface_name:
                        continue

                    key = (hostname, interface_name)
                    if key not in interface_references:
                        interface_references[key] = []
                    interface_references[key].append(network_name)

        return interface_references

    @classmethod
    def validate_access_interface_references(cls, access_interfaces_map, interface_references):
        """
        Validate access interface references against network attach groups
        """
        for key, interface_info in access_interfaces_map.items():
            hostname = interface_info['hostname']
            interface_name = interface_info['interface']
            has_access_vlan = interface_info['has_access_vlan']

            # Check if this interface is referenced in network attach groups
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

class Rule:
    id = "311"
    description = "Verify VPC port-channel consistency between peer switches"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        switches = []

        # Check for the 'switches' key in the data model
        dm_check = cls.data_model_key_check(
            inventory, ['vxlan', 'topology', 'switches']
        )
        if 'switches' in dm_check['keys_data']:
            switches = inventory['vxlan']['topology']['switches']

        # Check for VPC peers
        vpc_peers_check = cls.data_model_key_check(
            inventory, ['vxlan', 'topology', 'vpc_peers']
        )
        if 'vpc_peers' not in vpc_peers_check['keys_data']:
            return results  # No VPC peers defined, nothing to validate

        vpc_peers = inventory['vxlan']['topology']['vpc_peers']

        # Create a lookup dictionary for switches by name
        switch_lookup = {switch.get('name'): switch for switch in switches}

        # Iterate through VPC peer pairs
        for vpc_pair in vpc_peers:
            peer1_name = vpc_pair.get('peer1')
            peer2_name = vpc_pair.get('peer2')
            domain_id = vpc_pair.get('domain_id')

            peer1_switch = switch_lookup.get(peer1_name)
            peer2_switch = switch_lookup.get(peer2_name)

            if not peer1_switch or not peer2_switch:
                continue  # Skip if switches not found

            # Find VPC port-channels on each switch
            peer1_vpc_channels = cls.find_vpc_port_channels(peer1_switch)
            peer2_vpc_channels = cls.find_vpc_port_channels(peer2_switch)

            # Check if one peer has VPC port-channels but the other doesn't
            if peer1_vpc_channels and not peer2_vpc_channels:
                pc_names = [pc['name'] for pc in peer1_vpc_channels]
                results.append(
                    f"VPC pair (domain {domain_id}): Switch '{peer1_name}' "
                    f"has VPC port-channel(s) {pc_names}, but peer switch "
                    f"'{peer2_name}' has no VPC port-channels defined."
                )
            elif peer2_vpc_channels and not peer1_vpc_channels:
                pc_names = [pc['name'] for pc in peer2_vpc_channels]
                results.append(
                    f"VPC pair (domain {domain_id}): Switch '{peer2_name}' "
                    f"has VPC port-channel(s) {pc_names}, but peer switch "
                    f"'{peer1_name}' has no VPC port-channels defined."
                )
            elif peer1_vpc_channels and peer2_vpc_channels:
                # Both peers have VPC port-channels, validate they match
                results.extend(cls.validate_vpc_channel_consistency(
                    peer1_name, peer1_vpc_channels, peer2_name,
                    peer2_vpc_channels, domain_id
                ))

        return results

    @classmethod
    def find_vpc_port_channels(cls, switch):
        """Find all port-channels with mode 'vpc_pair' on a switch"""
        vpc_channels = []
        if switch.get('interfaces'):
            for interface in switch['interfaces']:
                interface_name = interface.get('name', '')
                is_pc = (interface_name.startswith('port-channel') or
                         interface_name.startswith('po'))
                if is_pc and interface.get('mode') == 'vpc_pair':
                    vpc_channels.append(interface)
        return vpc_channels

    @classmethod
    def validate_vpc_channel_consistency(cls, peer1_name, peer1_channels,
                                         peer2_name, peer2_channels,
                                         domain_id):
        """Validate that VPC port-channels are consistent between peers"""
        results = []

        # Check if the number of VPC port-channels match
        if len(peer1_channels) != len(peer2_channels):
            results.append(
                f"VPC pair (domain {domain_id}): Mismatch in number of "
                f"VPC port-channels - '{peer1_name}' has "
                f"{len(peer1_channels)}, '{peer2_name}' has "
                f"{len(peer2_channels)}"
            )
            return results

        # Sort channels by port-channel ID for comparison
        def get_pc_id(interface):
            return cls.extract_pc_id(interface.get('name', ''))

        peer1_sorted = sorted(peer1_channels, key=get_pc_id)
        peer2_sorted = sorted(peer2_channels, key=get_pc_id)

        # Compare each pair of port-channels
        for peer1_pc, peer2_pc in zip(peer1_sorted, peer2_sorted):
            peer1_pc_id = cls.extract_pc_id(peer1_pc.get('name', ''))
            peer2_pc_id = cls.extract_pc_id(peer2_pc.get('name', ''))

            # Check if port-channel IDs match
            if peer1_pc_id != peer2_pc_id:
                results.append(
                    f"VPC pair (domain {domain_id}): Port-channel ID "
                    f"mismatch - '{peer1_name}' has "
                    f"'{peer1_pc.get('name')}', '{peer2_name}' has "
                    f"'{peer2_pc.get('name')}'"
                )

            # Check if pc_mode matches (if defined on both)
            peer1_pc_mode = peer1_pc.get('pc_mode')
            peer2_pc_mode = peer2_pc.get('pc_mode')
            if (peer1_pc_mode and peer2_pc_mode and
                    peer1_pc_mode != peer2_pc_mode):
                results.append(
                    f"VPC pair (domain {domain_id}): Port-channel mode "
                    f"mismatch on PC{peer1_pc_id} - '{peer1_name}' has "
                    f"'{peer1_pc_mode}', '{peer2_name}' has "
                    f"'{peer2_pc_mode}'"
                )

            # Check if trunk_allowed_vlans matches (if defined on both)
            peer1_vlans = peer1_pc.get('trunk_allowed_vlans')
            peer2_vlans = peer2_pc.get('trunk_allowed_vlans')
            if peer1_vlans and peer2_vlans and peer1_vlans != peer2_vlans:
                results.append(
                    f"VPC pair (domain {domain_id}): VLAN configuration "
                    f"mismatch on PC{peer1_pc_id} - '{peer1_name}' allows "
                    f"'{peer1_vlans}', '{peer2_name}' allows "
                    f"'{peer2_vlans}'"
                )

        return results

    @classmethod
    def extract_pc_id(cls, interface_name):
        """Extract port-channel ID from interface name"""
        import re
        match = re.search(r'(?:port-channel|po)(\d+)', interface_name.lower())
        return int(match.group(1)) if match else 0

    @classmethod
    def data_model_key_check(cls, tested_object, keys):
        """
        Helper method to check the presence of keys in a nested dictionary.
        """
        dm_key_dict = {
            'keys_found': [], 'keys_not_found': [],
            'keys_data': [], 'keys_no_data': []
        }
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

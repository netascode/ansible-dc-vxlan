class Rule:
    id = "311"
    description = "Verify that ToRs being removed do not have networks attached"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        """
        Check if any networks are attached to ToR switches that are being removed.
        ToRs are considered "being removed" if they appear in tor_peers but not in 
        the switches inventory.
        """
        results = []
        
        # Get the list of switches in the topology
        switches_keys = ['vxlan', 'topology', 'switches']
        dm_check = cls.data_model_key_check(data_model, switches_keys)
        if 'switches' not in dm_check['keys_data']:
            return results
        
        switches = data_model['vxlan']['topology']['switches']
        switch_names = {sw['name'] for sw in switches if 'name' in sw}
        
        # Get ToR peers configuration
        tor_peers_keys = ['vxlan', 'topology', 'tor_peers']
        dm_check = cls.data_model_key_check(data_model, tor_peers_keys)
        
        # If no tor_peers defined, nothing to check
        if 'tor_peers' not in dm_check['keys_data']:
            return results
        
        tor_peers = data_model['vxlan']['topology']['tor_peers']
        
        # Collect all ToR switch names referenced in tor_peers
        tor_switch_names = set()
        for pairing in tor_peers:
            if 'tor1' in pairing:
                tor1_name = pairing['tor1'].get('name') if isinstance(pairing['tor1'], dict) else pairing['tor1']
                if tor1_name:
                    tor_switch_names.add(tor1_name)
            
            if 'tor2' in pairing:
                tor2_name = pairing['tor2'].get('name') if isinstance(pairing['tor2'], dict) else pairing['tor2']
                if tor2_name:
                    tor_switch_names.add(tor2_name)
        
        # Identify ToRs that are being removed (in tor_peers but NOT in switches inventory)
        removed_tors = tor_switch_names - switch_names
        
        # If no ToRs are being removed, no validation needed
        if not removed_tors:
            return results
        
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

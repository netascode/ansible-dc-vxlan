class Rule:
    id = "401"
    description = "Cross Reference VRFs and Networks items in the Service Model"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []

        switches = None
        vpc_peers = None
        sm_networks = None
        sm_vrfs = None
        network_attach_groups = None
        vrf_attach_groups = None

        switch_keys = ['vxlan', 'topology', 'switches']
        vpc_peers_keys = ['vxlan', 'topology', 'vpc_peers']

        # Remove the check for overlay_services after deprecation
        # Remove lines 21 - 23
        overlay_key = 'overlay'
        check = cls.data_model_key_check(data_model, ['vxlan', overlay_key])
        if overlay_key in check['keys_not_found'] or overlay_key in check['keys_no_data']:
            overlay_key = 'overlay_services'

        check = cls.data_model_key_check(data_model, ['vxlan', overlay_key])
        if overlay_key in check['keys_found'] and overlay_key in check['keys_data']:
            network_keys = ['vxlan', overlay_key, 'networks']
            vrf_keys = ['vxlan', overlay_key, 'vrfs']
            network_attach_keys = ['vxlan', overlay_key, 'network_attach_groups']
            vrf_attach_keys = ['vxlan', overlay_key, 'vrf_attach_groups']

            # Check if vrfs, network, switch, and vpc_peers data is defined in the service model
            check = cls.data_model_key_check(data_model, switch_keys)
            if 'switches' in check['keys_data']:
                switches = cls.safeget(data_model, switch_keys)
            if not switches:
                # No switches defined in the service model, no reason to continue
                return results

            check = cls.data_model_key_check(data_model, vpc_peers_keys)
            if 'vpc_peers' in check['keys_data']:
                vpc_peers = cls.safeget(data_model, vpc_peers_keys)

            check = cls.data_model_key_check(data_model, network_keys)
            if 'networks' in check['keys_data']:
                sm_networks = cls.safeget(data_model, network_keys)

            check = cls.data_model_key_check(data_model, vrf_keys)
            if 'vrfs' in check['keys_data']:
                sm_vrfs = cls.safeget(data_model, vrf_keys)

            check = cls.data_model_key_check(data_model, vrf_attach_keys)
            if 'vrf_attach_groups' in check['keys_data']:
                vrf_attach_groups = cls.safeget(data_model, vrf_attach_keys)

            check = cls.data_model_key_check(data_model, network_attach_keys)
            if 'network_attach_groups' in check['keys_data']:
                network_attach_groups = cls.safeget(data_model, network_attach_keys)

            # Ensure Network is not referencing a VRF that is not defined in the service model
            results = cls.cross_reference_vrfs_nets(sm_vrfs, sm_networks, results)

            if sm_vrfs and vrf_attach_groups:
                results = cls.cross_reference_switches(vrf_attach_groups, switches, 'vrf', results)
                results = cls.cross_reference_vpc_peers(vrf_attach_groups, vpc_peers, 'vrf', results)
            if sm_networks and network_attach_groups:
                results = cls.cross_reference_switches(network_attach_groups, switches, 'network', results)
                results = cls.cross_reference_vpc_peers(network_attach_groups, vpc_peers, 'network', results)

        return results

    @classmethod
    def data_model_key_check(cls, tested_object, keys):
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
        # Utility function to safely get nested dictionary values
        for key in keys:
            if dict is None:
                return None
            if key in dict:
                dict = dict[key]
            else:
                return None

        return dict

    @classmethod
    def cross_reference_vrfs_nets(cls, sm_vrfs, sm_networks, results):
        if not sm_vrfs or not sm_networks:
            return results

        vrf_names = []
        for vrf in sm_vrfs:
            vrf_names.append(vrf.get("name"))
        # Compare the two lists and generate an error message if a network is found
        # in network_vrf_names that is not in vrf_names
        for net in sm_networks:
            if net.get("vrf_name") is not None:
                if net.get("vrf_name") not in vrf_names:
                    results.append(
                        f"Network ({net.get('name')}) is referencing VRF ({net.get('vrf_name')}) "
                        "which is not defined in the service model. Add the VRF to the service model or remove the network from the service model "
                        "and re-run the playbook."
                    )

        return results

    @classmethod
    def cross_reference_switches(cls, attach_groups, switches, target, results):
        # target is either vrf or network
        for attach_group in attach_groups:
            for switch in attach_group.get("switches"):
                if switch.get("hostname"):
                    if not any(s.get("name") == switch.get("hostname") for s in switches):
                        if not any(s.get('management').get('management_ipv4_address') == switch.get("hostname") for s in switches):
                            if not any(s.get('management').get('management_ipv6_address') == switch.get("hostname") for s in switches):
                                ag = attach_group.get("name")
                                hn = switch.get("hostname")
                                results.append(f"{target} attach group {ag} hostname {hn} does not match any switch in the topology.")

        return results

    @classmethod
    def cross_reference_vpc_peers(cls, attach_groups, vpc_peers, target,results):
        """
        Check if each switch referenced in a vrf_attach_group or network_attach_group
        is part of a vpc_peers entry, either peer1 or peer2, and if the corresponding peer
        in the vpc_peers is also found in the vrf_attach_group.
        """

        if not attach_groups or not vpc_peers:
            return results

        # Build a mapping of vPC peers: hostname -> peer_hostname
        vpc_peer_mapping = {}
        for vpc_pair in vpc_peers:
            peer1 = vpc_pair.get('peer1')
            peer2 = vpc_pair.get('peer2')
            if peer1 and peer2:
                vpc_peer_mapping[peer1] = peer2
                vpc_peer_mapping[peer2] = peer1

        # Check each attach group
        for attach_group in attach_groups:
            group_name = attach_group.get('name')
            group_switches = attach_group.get('switches', [])

            # Get all hostnames in this attach group
            group_hostnames = set()
            for switch in group_switches:
                hostname = switch.get('hostname')
                if hostname:
                    group_hostnames.add(hostname)

            # Check for missing vPC peers
            for hostname in group_hostnames:
                if hostname in vpc_peer_mapping:
                    vpc_peer = vpc_peer_mapping[hostname]
                    if vpc_peer not in group_hostnames:
                        results.append(
                            f"{target}_attach_group '{group_name}' contains switch '{hostname}' "
                            f"which has vPC peer '{vpc_peer}', but the vPC peer is not included "
                            f"in the same attach group. Both vPC peers should be in the same attach group."
                        )

        return results

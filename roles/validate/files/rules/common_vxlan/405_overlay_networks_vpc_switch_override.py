class Rule:
    id = "405"
    description = "Verify Network vlan_id override attribute are the same on vPC Peers"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        networks = cls.safeget(data_model, ['vxlan', 'overlay', 'networks'])
        vpc_peers = cls.safeget(data_model, ['vxlan', 'topology', 'vpc_peers'])

        #  Build a mapping of vPC peers: hostname -> peer_hostname
        vpc_peer_mapping = {}
        for vpc_pair in vpc_peers:
            peer1 = vpc_pair.get('peer1')
            peer2 = vpc_pair.get('peer2')
            if peer1 and peer2:
                vpc_peer_mapping[peer1] = peer2
                vpc_peer_mapping[peer2] = peer1

        for network in networks:
            attach_overrides = cls.safeget(network,['switch_attach_overrides'])
            if attach_overrides:
                vlan_overrides = {o['hostname']: o.get('vlan_id') for o in attach_overrides}
                for override in attach_overrides:
                    switch = override['hostname']
                    vlan_override = cls.safeget(override,['vlan_id'])
                    if vlan_override:
                        if switch in vpc_peer_mapping:
                            peer = vpc_peer_mapping[switch]
                            peer_override = vlan_overrides.get(peer)
                            peer_vlan_id = peer_override if peer_override is not None else cls.safeget(network, ['vlan_id'])


                            if vlan_override != peer_vlan_id:
                                results.append(
                                f"Networks.{network['name']}: switches {switch} and {peer} "
                                f"are vPC peers but have different vlan_id: "
                                f"{vlan_override} != {peer_vlan_id}"
                                )

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

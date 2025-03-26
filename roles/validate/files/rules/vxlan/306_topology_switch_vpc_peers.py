class Rule:
    id = "30"
    description = "Verify a vPC peer exists in the topology.switches inventory"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        switches = []
        vpc_peers_pairs = []

        dm_check = cls.data_model_key_check(inventory, ['vxlan', 'topology', 'switches'])
        if 'switches' in dm_check['keys_data']:
            switches = inventory['vxlan']['topology']['switches']
        else:
            return results

        vpc_peers_keys = ['vxlan', 'topology', 'vpc_peers']
        dm_check = cls.data_model_key_check(inventory, vpc_peers_keys)
        if 'vpc_peers' in dm_check['keys_found'] and 'vpc_peers' in dm_check['keys_data']:
            vpc_peers_pairs = inventory['vxlan']['topology']['vpc_peers']
            for vpc_peers_pair in vpc_peers_pairs:
                if any(sw['name'] == vpc_peers_pair['peer1'] for sw in switches):
                    pass
                else:
                    results.append(
                        f"vxlan.topology.vpc_peers switch {vpc_peers_pair['peer1']} not found in the topology inventory."
                    )
                if any(sw['name'] == vpc_peers_pair['peer2'] for sw in switches):
                    pass
                else:
                    results.append(
                        f"vxlan.topology.vpc_peers switch {vpc_peers_pair['peer2']} not found in the topology inventory."
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

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

        dm_check = cls.data_model_key_check(inventory, ['vxlan', 'global', 'vpc', 'domain_id_range'])
        if 'domain_id_range' in dm_check['keys_data']:
            vpc_range = inventory['vxlan']['global']['vpc']['domain_id_range']
        else:
            vpc_range = "1-1000"
        vpc_range_split = vpc_range.split("-")
        vpc_domain_list = []

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

                if vpc_peers_pair['domain_id'] > int(vpc_range_split[1]) or vpc_peers_pair['domain_id'] < int(vpc_range_split[0]) :
                    results.append(
                        f"vxlan.topology.vpc_peers Domain ID {vpc_peers_pair['domain_id']} between {vpc_peers_pair['peer1']} {vpc_peers_pair['peer2']} "
                        f"vpc domain not in range: " + vpc_range + "."
                    )

                if vpc_peers_pair['domain_id'] not in vpc_domain_list:
                    vpc_domain_list.append(vpc_peers_pair['domain_id'])
                else:
                    results.append(
                        f"vxlan.topology.vpc_peers Domain ID {vpc_peers_pair['domain_id']} is duplicated.")
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

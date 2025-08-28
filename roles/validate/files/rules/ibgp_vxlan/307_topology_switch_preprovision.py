class Rule:
    id = "307"
    description = "Verify subnet is defined when preprovision is set"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        switches = []

        dm_check = cls.data_model_key_check(inventory, ['vxlan', 'topology', 'switches'])
        if 'switches' in dm_check['keys_data']:
            switches = inventory['vxlan']['topology']['switches']

        for switch in switches:
            dm_check = cls.data_model_key_check(switch, ['poap', 'preprovision'])
            if 'preprovision' in dm_check['keys_data']:
                dm_check = cls.data_model_key_check(switch, ['management', 'subnet_mask_ipv4'])
                if 'subnet_mask_ipv4' in dm_check['keys_not_found'] or 'subnet_mask_ipv4' in dm_check['keys_no_data']:
                    results.append(
                        f"vxlan.topology.switches.{switch['name']}.subnet_mask_ipv4 must be defined when preprovision is used."
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

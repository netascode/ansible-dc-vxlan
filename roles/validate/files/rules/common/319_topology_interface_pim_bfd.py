class Rule:
    id = "319"
    description = "Verify enable_pim_bfd_instance is only enabled when enable_pim_sparse is true"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        switches_check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' not in switches_check['keys_data']:
            return results

        switches = data_model['vxlan']['topology']['switches']
        for switch in switches:
            for interface in switch.get('interfaces', []):
                pim_bfd = interface.get('enable_pim_bfd_instance', None)
                pim_sparse = interface.get('enable_pim_sparse', None)
                if pim_bfd is True and pim_sparse is not True:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"enable_pim_bfd_instance=true requires "
                        f"enable_pim_sparse=true on the same interface."
                    )
        return results

    @classmethod
    def data_model_key_check(cls, tested_object, keys):
        dm_key_dict = {
            'keys_found': [], 'keys_not_found': [],
            'keys_data': [], 'keys_no_data': [],
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

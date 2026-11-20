class Rule:
    id = "326"
    description = "Verify SVI secondary gateways: secondary_gws require a primary ipv4_address on the SVI; at most 16 entries"
    severity = "HIGH"

    MAX_SECONDARY_GWS = 16

    @classmethod
    def match(cls, data_model):
        results = []
        switches_check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' not in switches_check['keys_data']:
            return results

        switches = data_model['vxlan']['topology']['switches']
        for switch in switches:
            for interface in switch.get('interfaces', []):
                secondary_gws = interface.get('secondary_gws')
                if not secondary_gws:
                    continue

                # Check 1: secondary_gws require a primary ipv4_address on the SVI
                if interface.get('ipv4_address') is None:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"secondary_gws require a primary ipv4_address on the SVI."
                    )

                # Check 2: at most 16 secondary gateways
                if len(secondary_gws) > cls.MAX_SECONDARY_GWS:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"secondary_gws has {len(secondary_gws)} entries; "
                        f"at most {cls.MAX_SECONDARY_GWS} are supported."
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

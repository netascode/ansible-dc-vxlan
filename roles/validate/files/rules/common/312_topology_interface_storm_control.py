class Rule:
    id = "312"
    description = "Verify either percentage or PPS is configured for storm-control"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        switches = []
        pct_keys = {'storm_control_broadcast_level_percent', 'storm_control_multicast_level_percent', 'storm_control_unicast_level_percent'}
        pps_keys = {'storm_control_broadcast_level_pps', 'storm_control_multicast_level_pps', 'storm_control_unicast_level_pps'}

        check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' in check['keys_data']:
            switches = data_model.get('vxlan').get('topology').get('switches')
        else:
            return results

        for switch in switches:
            check = cls.data_model_key_check(switch, ['interfaces'])
            if 'interfaces' in check['keys_data']:
                interfaces = switch.get('interfaces')
                for interface in interfaces:
                    pct = {k for k in pct_keys if interface.get(k) is not None}
                    pps = {k for k in pps_keys if interface.get(k) is not None}
                    if pct and pps:
                        results.append(
                            f"switch {switch.get('name')} interface {interface.get('name')}: "
                            f"storm_control percent and pps are mutually exclusive; "
                            f"got {sorted(pct)} and {sorted(pps)}"
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

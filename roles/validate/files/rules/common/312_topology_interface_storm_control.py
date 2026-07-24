class Rule:
    id = "312"
    description = "Verify either percentage or PPS is configured on the switch for storm-control"
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
                pct_ifaces = []
                pps_ifaces = []
                for interface in switch.get('interfaces'):
                    if any(interface.get(k) is not None for k in pct_keys):
                        pct_ifaces.append(interface.get('name'))
                    if any(interface.get(k) is not None for k in pps_keys):
                        pps_ifaces.append(interface.get('name'))

                if pct_ifaces and pps_ifaces:
                    results.append(
                        f"switch {switch.get('name')}: storm_control mode must be consistent "
                        f"across all interfaces; percent-mode interfaces: {pct_ifaces}; "
                        f"pps-mode interfaces: {pps_ifaces}"
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

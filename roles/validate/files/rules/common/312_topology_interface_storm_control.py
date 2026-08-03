class Rule:
    id = "312"
    description = "Verify either percentage or PPS is configured on each interface for storm-control (not both)"
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

        level_keys = pct_keys | pps_keys

        for switch in switches:
            for interface in switch.get('interfaces', []):
                enabled = interface.get('enable_storm_control', False)
                action = interface.get('storm_control_action')
                configured_levels = sorted(
                    k for k in level_keys if interface.get(k) is not None
                )

                if not enabled:
                    invalid_keys = list(configured_levels)
                    if action not in (None, 'default'):
                        invalid_keys.append('storm_control_action')

                    if invalid_keys:
                        results.append(
                            f"switch {switch.get('name')} "
                            f"interface {interface.get('name')}: "
                            "storm_control action and level fields require "
                            "enable_storm_control: true; "
                            f"invalid keys: {sorted(invalid_keys)}"
                        )
                    continue

                pct_set = sorted(
                    k for k in pct_keys if interface.get(k) is not None
                )
                pps_set = sorted(
                    k for k in pps_keys if interface.get(k) is not None
                )

                if pct_set and pps_set:
                    results.append(
                        f"switch {switch.get('name')} "
                        f"interface {interface.get('name')}: "
                        "storm_control cannot mix percent and pps "
                        "on the same interface; "
                        f"percent keys: {pct_set}; pps keys: {pps_set}"
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

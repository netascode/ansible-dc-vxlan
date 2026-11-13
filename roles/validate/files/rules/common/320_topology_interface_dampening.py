class Rule:
    id = "320"
    description = "Verify dampening sub-fields require enable_dampening=true and satisfy field dependencies"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        switches_check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' not in switches_check['keys_data']:
            return results

        sub_fields = [
            'dampening_half_life', 'dampening_reuse', 'dampening_suppress',
            'dampening_max_suppress', 'dampening_restart', 'dampening_restart_penalty',
        ]

        switches = data_model['vxlan']['topology']['switches']
        for switch in switches:
            for interface in switch.get('interfaces', []):
                enable = interface.get('enable_dampening', None)

                sub_set = [f for f in sub_fields if interface.get(f) is not None]
                if sub_set and enable is not True:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"dampening sub-fields ({', '.join(sub_set)}) require "
                        f"enable_dampening=true on the same interface."
                    )

                if interface.get('dampening_reuse') is not None and interface.get('dampening_half_life') is None:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"dampening_reuse requires dampening_half_life to be set."
                    )

                if interface.get('dampening_restart_penalty') is not None and interface.get('dampening_restart') is not True:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"dampening_restart_penalty requires dampening_restart=true on the same interface."
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

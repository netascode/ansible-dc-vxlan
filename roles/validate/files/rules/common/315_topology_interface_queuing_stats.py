class Rule:
    id = "315"
    description = (
        "Verify that enable_queuing_stats is only set on interfaces where "
        "queuing_policy is defined."
    )
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        switches = []

        check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' in check['keys_data']:
            switches = data_model.get('vxlan').get('topology').get('switches')
        else:
            return results

        for switch in switches:
            for interface in switch.get('interfaces', []) or []:
                if 'enable_queuing_stats' not in interface:
                    continue
                if not interface.get('queuing_policy'):
                    results.append(
                        f"vxlan.topology.switches.{switch.get('name')}."
                        f"interfaces.{interface.get('name')}.enable_queuing_stats: "
                        "is set but queuing_policy is not defined; the "
                        "DISABLE_QUEUING_STATS field will not be emitted to NDFC. "
                        "Set queuing_policy on the interface, or remove "
                        "enable_queuing_stats."
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

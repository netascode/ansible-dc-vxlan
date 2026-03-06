class Rule:
    id = "301"
    description = "Verify a switch's serial number exists in the topology inventory"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        switches = []

        check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' in check['keys_data']:
            switches = data_model.get("vxlan").get("topology").get("switches")
        else:
            return results

        for switch in switches:
            if not switch.get("serial_number", False):
                results.append(
                    f"vxlan.topology.switches.{switch['name']} serial number must be defined at least once in the topology inventory."
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

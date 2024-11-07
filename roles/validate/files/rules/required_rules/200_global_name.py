class Rule:
    id = "200"
    description = "Verify global data model contains fabric / host_vars name."
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []

        global_keys = ['vxlan', 'global', 'name']

        # Check if name data is defined in the data model
        check = cls.data_model_key_check(inventory, global_keys)
        if 'name' not in check['keys_found']:
            results.append("vxlan.global.name is not defined in the data model.")

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

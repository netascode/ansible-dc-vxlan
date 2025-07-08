class Rule:
    id = "206"
    description = "Verify fabric VNI and VLAN ranges."
    severity = "HIGH"

    results = []

    @classmethod
    def match(cls, inventory):

        for key in ['layer2_vni_range', 'layer3_vni_range', 'layer2_vlan_range', 'layer3_vlan_range']:
            cls.check_ranges(key, 'VNI' if 'vni' in key else 'VLAN', inventory)

        return cls.results

    @classmethod
    def check_ranges(cls, check_key, range_type, data):
        start_keys = ['vxlan', 'global', check_key, 'from']
        end_keys = ['vxlan', 'global', check_key, 'to']
        check_start = cls.data_model_key_check(data, start_keys)
        check_end = cls.data_model_key_check(data, end_keys)

        if (
            ('from' in check_start['keys_data']) and
            ('to' in check_end['keys_data'])
        ):
            vni_start = cls.safeget(data, start_keys)
            vni_end = cls.safeget(data, end_keys)

            if vni_start and vni_end:
                if int(vni_start) >= int(vni_end):
                    cls.results.append(f"When defining {range_type} range, {check_key}, 'from' must be less than 'to'.")
                    return cls.results
            else:
                cls.results.append(f"When defining {range_type} range, {check_key}, both 'from' and 'to' must have valid data.")
                return cls.results

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

    @classmethod
    def safeget(cls, dict, keys):
        # Utility function to safely get nested dictionary values
        for key in keys:
            if dict is None:
                return None
            if key in dict:
                dict = dict[key]
            else:
                return None

        return dict

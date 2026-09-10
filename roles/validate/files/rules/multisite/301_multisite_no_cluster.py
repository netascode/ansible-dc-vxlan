class Rule:
    id = "301"
    description = "Verify MSD fabric does not reference clusters"
    severity = "LOW"

    msg = "{0} multisite child fabric should not reference clusters"

    @classmethod
    def match(cls, data_model):
        results = []

        fabric_type = ''

        vxlan_fabric_keys = ['vxlan', 'fabric']
        check = cls.data_model_key_check(data_model, vxlan_fabric_keys)
        if 'fabric' in check['keys_found'] and 'fabric' in check['keys_data']:
            dm_fabric = cls.safeget(data_model, vxlan_fabric_keys)
            fabric_type = dm_fabric.get('type', '')

        multisite_child_fabric_keys = ['vxlan', 'multisite', 'child_fabrics']
        check = cls.data_model_key_check(data_model, multisite_child_fabric_keys)
        if 'child_fabrics' in check['keys_found'] and 'child_fabrics' in check['keys_data']:
            dm_child_fabrics = cls.safeget(data_model, multisite_child_fabric_keys)
            for child_fabric in dm_child_fabrics:
                if fabric_type == 'MSD' and child_fabric.get('cluster', False):
                    results.append(cls.msg.format(child_fabric['name']))

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

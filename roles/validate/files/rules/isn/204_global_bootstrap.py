class Rule:
    id = "204"
    description = "Verify Bootstrap Configuration"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []

        # v4 bootstrap check
        bootstrap_keys = ['vxlan', 'global', 'bootstrap', 'dhcp_v4', 'domain_name']
        check = cls.data_model_key_check(inventory, bootstrap_keys)
        if 'domain_name' in check['keys_not_found']:
            results.append(f"vxlan.global.bootstrap.domain_name is required for bootstrap in an ISN type fabric.")

        # v6 bootstrap check
        bootstrap_keys = ['vxlan', 'global', 'bootstrap', 'dhcp_v6', 'domain_name']
        check = cls.data_model_key_check(inventory, bootstrap_keys)
        if 'domain_name' in check['keys_not_found']:
            results.append(f"vxlan.global.bootstrap.domain_name is required for bootstrap in an ISN type fabric.")

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
class Rule:
    id = "001"
    description = "Verify the data model for what should be supported via child fabric(s)"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []

        # Keys supported via child fabric(s)
        child_fabric_supported_keys = ['global', 'topology', 'underlay', 'overlay_extensions', 'policy']
        for child_fabric_supported_key in child_fabric_supported_keys:
            check = cls.data_model_key_check(data_model, ['vxlan', child_fabric_supported_key])
            if child_fabric_supported_key in check['keys_found']:
                results.append(
                    f"Key '{child_fabric_supported_key}' is supported via child fabric(s) respective host_vars data model file(s) "
                    f"and should not be present in the multisite parent fabric data model host_vars file(s)."
                )

                return results

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

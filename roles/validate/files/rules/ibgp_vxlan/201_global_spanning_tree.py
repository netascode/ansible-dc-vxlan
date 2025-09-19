class Rule:
    id = "201"
    description = "Verify a spanning tree protocol mutually exclusive parameters."
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []

        stp_keys = ['vxlan', 'global', 'ibgp']
        check = cls.data_model_key_check(data_model, stp_keys)
        stp_keys.append('spanning_tree')
        if 'ibgp' in check['keys_not_found'] or cls.safeget(data_model, stp_keys) is None:
        # Backwards compatibility check for vxlan.global.spanning_tree
            stp_keys = ['vxlan', 'global', 'spanning_tree']
            check = cls.data_model_key_check(data_model, stp_keys)

        root_bridge_protocol = cls.safeget(data_model, stp_keys + ['root_bridge_protocol'])
        vlan_range = cls.safeget(data_model, stp_keys + ['vlan_range'])
        mst_instance_range = cls.safeget(data_model, stp_keys + ['mst_instance_range'])

        if vlan_range and mst_instance_range:
            results.append(
                "vxlan.global.ibgp.spanning_tree.vlan_range and vxlan.global.ibgp.spanning_tree.mst_instance_range "
                "both cannot be configured at the same time. Please choose one depending on the "
                "vxlan.global.ibgp.spanning_tree.root_bridge_protocol selected."
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

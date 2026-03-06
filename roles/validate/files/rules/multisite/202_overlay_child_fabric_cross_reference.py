class Rule:
    id = "202"
    description = "Cross reference VRFs and Networks child fabric references"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        child_fabrics_names = []
        vrfs = []
        networks = []

        multisite_child_fabric_keys = ['vxlan', 'multisite', 'child_fabrics']
        check = cls.data_model_key_check(data_model, multisite_child_fabric_keys)
        if 'child_fabrics' in check['keys_found'] and 'child_fabrics' in check['keys_data']:
            child_fabrics_names = [child_fabric['name'] for child_fabric in data_model['vxlan']['multisite']['child_fabrics']]

        multisite_vrf_keys = ['vxlan', 'multisite', 'overlay', 'vrfs']
        check = cls.data_model_key_check(data_model, multisite_vrf_keys)
        if 'vrfs' in check['keys_found'] and 'vrfs' in check['keys_data']:
            vrfs = data_model['vxlan']['multisite']['overlay']['vrfs']
            results = cls.cross_reference_child_fabrics(child_fabrics_names, vrfs, results)

        multisite_network_keys = ['vxlan', 'multisite', 'overlay', 'networks']
        check = cls.data_model_key_check(data_model, multisite_network_keys)
        if 'networks' in check['keys_found'] and 'networks' in check['keys_data']:
            networks = data_model['vxlan']['multisite']['overlay']['networks']
            results = cls.cross_reference_child_fabrics(child_fabrics_names, networks, results)

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

    @classmethod
    def cross_reference_child_fabrics(cls, child_fabrics, overlay_items, results):
        for overlay_item in overlay_items:
            if overlay_item.get("child_fabrics"):
                for overlay_item_child_fabric in overlay_item["child_fabrics"]:
                    if overlay_item_child_fabric.get("name") not in child_fabrics:
                        results.append(
                            f"{overlay_item.get('name')} references child fabric {overlay_item_child_fabric.get('name')} "
                            "which is not defined in the data model. Add the child fabric to the data model or remove the reference "
                            "and re-run the playbook."
                        )

        return results

class Rule:
    id = "401"
    description = "Cross Reference VRFs and Networks items in the Service Model"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []

        sm_networks = None
        sm_vrfs = None

        check = cls.data_model_key_check(inventory, ['vxlan', 'multisite', 'overlay'])
        if 'overlay' in check['keys_found'] and 'overlay' in check['keys_data']:
            network_keys = ['vxlan', 'multisite', 'overlay', 'networks']
            vrf_keys = ['vxlan', 'multisite', 'overlay', 'vrfs']

            check = cls.data_model_key_check(inventory, network_keys)
            if 'networks' in check['keys_data']:
                sm_networks = cls.safeget(inventory, network_keys)

            check = cls.data_model_key_check(inventory, vrf_keys)
            if 'vrfs' in check['keys_data']:
                sm_vrfs = cls.safeget(inventory, vrf_keys)

            # Ensure Network is not referencing a VRF that is not defined in the service model
            results = cls.cross_reference_vrfs_nets(sm_vrfs, sm_networks, results)

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
    def cross_reference_vrfs_nets(cls, sm_vrfs, sm_networks, results):
        if not sm_vrfs or not sm_networks:
            return results

        vrf_names = []
        for vrf in sm_vrfs:
            vrf_names.append(vrf.get("name"))
        # Compare the two lists and generate an error message if a network is found
        # in network_vrf_names that is not in vrf_names
        for net in sm_networks:
            if net.get("vrf_name") is not None:
                if net.get("vrf_name") not in vrf_names:
                    results.append(
                        f"Network ({net.get('name')}) is referencing VRF ({net.get('vrf_name')}) "
                        "which is not defined in the service model. Add the VRF to the service model or remove the network from the service model "
                        "and re-run the playbook."
                    )

        return results

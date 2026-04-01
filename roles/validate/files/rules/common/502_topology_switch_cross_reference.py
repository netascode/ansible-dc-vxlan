class Rule:
    id = "502"
    description = "Verify enable_bootstrap is true when poap is defined on a switch"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        switches = []

        dm_check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' in dm_check['keys_data']:
            switches = data_model['vxlan']['topology']['switches']

        # Check if any switch has a poap key defined
        poap_switches = []
        for switch in switches:
            dm_check = cls.data_model_key_check(switch, ['poap'])
            if 'poap' in dm_check['keys_data']:
                poap_switches.append(switch['name'])

        if not poap_switches:
            return results

        # Map fabric types to the keys used in the data model
        fabric_type_map = {
            "VXLAN_EVPN": "ibgp",
            "eBGP_VXLAN": "ebgp",
            "External": "external"
        }

        fabric_type = fabric_type_map.get(data_model['vxlan']['fabric']['type'])

        # Check for enable_bootstrap under fabric-type-specific path first
        enable_bootstrap = None
        bootstrap_keys = ['vxlan', 'global', fabric_type, 'bootstrap', 'enable_bootstrap']
        check = cls.data_model_key_check(data_model, bootstrap_keys)
        if 'enable_bootstrap' in check['keys_data']:
            enable_bootstrap = cls.safeget(data_model, bootstrap_keys)

        # Fall back to the common path if not found under fabric-type-specific path
        if enable_bootstrap is None:
            bootstrap_keys = ['vxlan', 'global', 'bootstrap', 'enable_bootstrap']
            check = cls.data_model_key_check(data_model, bootstrap_keys)
            if 'enable_bootstrap' in check['keys_data']:
                enable_bootstrap = cls.safeget(data_model, bootstrap_keys)

        if enable_bootstrap is not True:
            for switch_name in poap_switches:
                results.append(
                    f"vxlan.topology.switches.{switch_name} has poap defined but "
                    f"vxlan.global.bootstrap.enable_bootstrap is not set to true."
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
        for key in keys:
            if dict is None:
                return None
            if key in dict:
                dict = dict[key]
            else:
                return None
        return dict

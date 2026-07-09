class Rule:
    id = "204"
    description = "Verify bootstrap configuration"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        switches = []
        dhcp = None

        # Map fabric types to the keys used in the data model based on controller fabric types
        fabric_type_map = {
            "VXLAN_EVPN": "ibgp",
            "eBGP_VXLAN": "ebgp",
            "External": "external"
        }

        fabric_type = fabric_type_map.get(data_model['vxlan']['fabric']['type'])

        bootstrap_keys = ['vxlan', 'global', fabric_type]
        check = cls.data_model_key_check(data_model, bootstrap_keys)
        if fabric_type in check['keys_found']:
            bootstrap_keys = ['vxlan', 'global', fabric_type, 'bootstrap', 'enable_bootstrap']
            check = cls.data_model_key_check(data_model, bootstrap_keys)

        if fabric_type in check['keys_not_found'] or 'enable_bootstrap' in check['keys_not_found']:
            bootstrap_keys = ['vxlan', 'global', 'bootstrap', 'enable_bootstrap']
            check = cls.data_model_key_check(data_model, bootstrap_keys)

        if 'enable_bootstrap' in check['keys_found']:
            if fabric_type in bootstrap_keys:
                bootstrap_keys = ['vxlan', 'global', fabric_type, 'bootstrap', 'enable_local_dhcp_server']
            else:
                bootstrap_keys = ['vxlan', 'global', 'bootstrap', 'enable_local_dhcp_server']
            check = cls.data_model_key_check(data_model, bootstrap_keys)
            enable_local_dhcp_server = cls.safeget(data_model, bootstrap_keys)
            if 'enable_local_dhcp_server' in check['keys_found'] and enable_local_dhcp_server:
                if fabric_type in bootstrap_keys:
                    bootstrap_keys = ['vxlan', 'global', fabric_type, 'bootstrap', 'dhcp_version']
                else:
                    bootstrap_keys = ['vxlan', 'global', 'bootstrap', 'dhcp_version']
                check = cls.data_model_key_check(data_model, bootstrap_keys)
                if 'dhcp_version' in check['keys_found']:
                    if cls.safeget(data_model, bootstrap_keys) == 'DHCPv4':
                        dhcp = 'dhcp_v4'
                    elif cls.safeget(data_model, bootstrap_keys) == 'DHCPv6':
                        dhcp = 'dhcp_v6'
                else:
                    results.append(f"A vxlan.global.{fabric_type}.bootstrap.dhcp_version is required for bootstrap in a VXLAN type fabric.")
                    return results

        if dhcp:
            if fabric_type in bootstrap_keys:
                bootstrap_keys = ['vxlan', 'global', fabric_type, 'bootstrap', dhcp, 'domain_name']
            else:
                bootstrap_keys = ['vxlan', 'global', 'bootstrap', dhcp, 'domain_name']
            check = cls.data_model_key_check(data_model, bootstrap_keys)
            if dhcp in check['keys_not_found']:
                results.append(
                    "When vxlan.global.bootstrap.dhcp_version is defined, either "
                    "vxlan.global.bootstrap.dhcpv4 or vxlan.global.bootstrap.dhcpv6 must be defined in the data model."
                )
                return results

            if 'domain_name' in check['keys_found'] and fabric_type in ("ibgp", "ebgp"):
                results.append(f"vxlan.global.bootstrap.{dhcp}.domain_name is not supported for bootstrap in a VXLAN type fabric.")
            elif 'domain_name' in check['keys_not_found'] and fabric_type == "external":
                results.append(f"vxlan.global.bootstrap.{dhcp}.domain_name is required for bootstrap in an External type fabric.")

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

        enable_bootstrap = None
        bootstrap_enable_keys = ['vxlan', 'global', fabric_type, 'bootstrap', 'enable_bootstrap']
        check = cls.data_model_key_check(data_model, bootstrap_enable_keys)
        if 'enable_bootstrap' in check['keys_found']:
            enable_bootstrap = cls.safeget(data_model, bootstrap_enable_keys)

        # Fall back to the common path if not found under fabric-type-specific path
        if enable_bootstrap is None:
            bootstrap_enable_keys = ['vxlan', 'global', 'bootstrap', 'enable_bootstrap']
            check = cls.data_model_key_check(data_model, bootstrap_enable_keys)
            if 'enable_bootstrap' in check['keys_found']:
                enable_bootstrap = cls.safeget(data_model, bootstrap_enable_keys)

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
        # Utility function to safely get nested dictionary values
        for key in keys:
            if dict is None:
                return None
            if key in dict:
                dict = dict[key]
            else:
                return None

        return dict

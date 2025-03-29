class Rule:
    id = "204"
    description = "Verify Bootstrap Configuration"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        dhcp = None

        bootstrap_keys = ['vxlan', 'multisite', 'isn', 'bootstrap', 'dhcp_version']
        check = cls.data_model_key_check(inventory, bootstrap_keys)
        if 'dhcp_version' in check['keys_found']:
            if inventory['vxlan']['multisite']['isn']['bootstrap']['dhcp_version'] == 'DHCPv4':
                dhcp = 'dhcp_v4'
            elif inventory['vxlan']['multisite']['isn']['bootstrap']['dhcp_version'] == 'DHCPv6':
                dhcp = 'dhcp_v6'
        else:
            results.append("A vxlan.multisite.isn.bootstrap.dhcp_version is required for bootstrap in an ISN type fabric.")
            return results

        if dhcp:
            bootstrap_keys = ['vxlan', 'multisite', 'isn', 'bootstrap', dhcp, 'domain_name']
            check = cls.data_model_key_check(inventory, bootstrap_keys)
            if dhcp in check['keys_not_found']:
                results.append(
                    "When vxlan.multisite.isn.bootstrap.dhcp_version is defined, either "
                    "vxlan.multisite.isn.bootstrap.dhcpv4 or vxlan.multisite.isn.bootstrap.dhcpv6 must be defined in the data model."
                )
                return results
            if 'domain_name' in check['keys_not_found']:
                results.append(f"vxlan.multisite.isn.bootstrap.{dhcp}.domain_name is required for bootstrap in an ISN type fabric.")

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

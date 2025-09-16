class Rule:
    id = "200"
    description = "Verify BGP ASN is defined for iBGP VXLAN and External fabric types."
    severity = "HIGH"

    @classmethod
    def match(cls, data):
        results = []

        fabric_type_map = {
            "VXLAN_EVPN": "ibgp",
            "External": "external"
        }

        fabric_type = None
        fabric_type = fabric_type_map.get(data["vxlan"]["fabric"].get("type"))

        # If we check keys vxlan.global.{fabric_type}.bgp_asn then this natively checks for this path
        # as well as the legacy vxlan.global path. Examples:
        # {'keys_found': ['vxlan', 'global', 'bgp_asn'], 'keys_not_found': ['ibgp'], 'keys_data': ['vxlan', 'global'], 'keys_no_data': ['bgp_asn']}
        # {'keys_found': ['vxlan', 'global', 'ibgp', 'bgp_asn'], 'keys_not_found': [], 'keys_data': ['vxlan', 'global', 'ibgp'], 'keys_no_data': ['bgp_asn']}
        check = cls.data_model_key_check(data, ['vxlan', 'global', fabric_type, 'bgp_asn'])
        if 'bgp_asn' not in check['keys_found']:
            results.append(f"vxlan.global.{fabric_type}.bgp_asn must be defined in the data model.")
        elif 'bgp_asn' in check['keys_found'] and 'bgp_asn' in check['keys_no_data']:
            results.append(f"vxlan.global.{fabric_type}.bgp_asn must have a value defined in the data model.")

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

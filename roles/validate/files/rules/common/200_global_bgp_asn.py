class Rule:
    id = "200"
    description = "Verify BGP ASN is defined for iBGP VXLAN and External fabric types."
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []

        dm_fabric_type = None
        fabric_type_keys = ['vxlan', 'fabric', 'type']
        check_fabric_type_key = cls.data_model_key_check(data_model, fabric_type_keys)
        if 'type' in check_fabric_type_key['keys_found'] and 'type' in check_fabric_type_key['keys_data']:
            dm_fabric_type = data_model['vxlan']['fabric']['type']

        if dm_fabric_type:
            # Map fabric types to the keys used in the data model based on controller fabric types
            fabric_type_map = {
                "VXLAN_EVPN": "ibgp",
                "eBGP_VXLAN": "ebgp",
                "External": "external"
            }

            fabric_type = fabric_type_map.get(dm_fabric_type)

            if fabric_type in ["ibgp", "external"]:
                # If we check keys vxlan.global.{fabric_type}.bgp_asn then this natively checks for this path
                # as well as the legacy vxlan.global path. Examples:
                # {'keys_found': ['vxlan', 'global'], 'keys_not_found': ['ibgp'], 'keys_data': ['vxlan', 'global'], 'keys_no_data': ['bgp_asn']} # noqa: E501
                # {'keys_found': ['vxlan', 'global', 'ibgp'], 'keys_not_found': ['bgp_asn'], 'keys_data': ['vxlan', 'global', 'ibgp'], 'keys_no_data': ['bgp_asn']} # noqa: E501
                check = cls.data_model_key_check(data_model, ['vxlan', 'global', fabric_type, 'bgp_asn'])
                if 'bgp_asn' in check['keys_not_found']:
                    check = cls.data_model_key_check(data_model, ['vxlan', 'global', 'bgp_asn'])
                    if 'bgp_asn' in check['keys_not_found']:
                        results.append(f"vxlan.global.{fabric_type}.bgp_asn must be defined in the data model.")
                        return results

                # {'keys_found': ['vxlan', 'global', 'bgp_asn'], 'keys_not_found': [], 'keys_data': ['vxlan', 'global'], 'keys_no_data': ['bgp_asn']} # noqa: E501
                # {'keys_found': ['vxlan', 'global', 'ibgp', 'bgp_asn'], 'keys_not_found': [], 'keys_data': ['vxlan', 'global', 'ibgp'], 'keys_no_data': ['bgp_asn']} # noqa: E501
                if 'bgp_asn' in check['keys_found'] and 'bgp_asn' in check['keys_no_data']:
                    results.append(f"vxlan.global.{fabric_type}.bgp_asn must have a value defined in the data model.")
                    return results

            if fabric_type in ["ebgp"]:
                # Since ebgp keys are only supported under vxlan.global.ebgp we need to ensure the ebgp key exists
                check = cls.data_model_key_check(data_model, ['vxlan', 'global', fabric_type])
                if 'ebgp' in check['keys_not_found']:
                    results.append(f"Fabric type is 'ebgp'.  Key vxlan.global.{fabric_type} must be defined in the data model.")
                    return results

                # Examples:
                # {'keys_found': ['vxlan', 'global', 'ebgp'], 'keys_not_found': ['spine_bgp_asn'], 'keys_data': ['vxlan', 'global', 'ebgp'], 'keys_no_data': []} # noqa: E501
                check = cls.data_model_key_check(data_model, ['vxlan', 'global', fabric_type, 'spine_bgp_asn'])
                if 'spine_bgp_asn' in check['keys_not_found']:
                    results.append(f"vxlan.global.{fabric_type}.spine_bgp_asn must be defined in the data model.")
                    return results

                # Examples:
                # {'keys_found': ['vxlan', 'global', 'ebgp', 'spine_bgp_asn'], 'keys_not_found': [], 'keys_data': ['vxlan', 'global', 'ebgp'], 'keys_no_data': ['spine_bgp_asn']} # noqa: E501
                if 'spine_bgp_asn' in check['keys_found'] and 'spine_bgp_asn' in check['keys_no_data']:
                    results.append(f"vxlan.global.{fabric_type}.spine_bgp_asn must have a value defined in the data model.")
                    return results

        else:
            results.append("vxlan.fabric.type must be defined in the data model.")
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

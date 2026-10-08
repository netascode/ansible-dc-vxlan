class Rule:
    id = "327"
    description = (
        "Verify PVLAN host interface configuration: pvlan_mode is required; "
        "pvlan_association applies only to 'host'/'trunk secondary'; "
        "pvlan_mapping applies only to 'promiscuous'/'trunk promiscuous'; "
        "native_vlan/trunk_allowed_vlans apply only to trunk submodes"
    )
    severity = "HIGH"

    ASSOCIATION_MODES = ('host', 'trunk secondary')
    MAPPING_MODES = ('promiscuous', 'trunk promiscuous')
    TRUNK_MODES = ('trunk promiscuous', 'trunk secondary')

    @classmethod
    def match(cls, data_model):
        results = []
        switches_check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' not in switches_check['keys_data']:
            return results

        switches = data_model['vxlan']['topology']['switches']
        for switch in switches:
            for interface in switch.get('interfaces', []):
                if interface.get('mode') != 'pvlan':
                    continue

                prefix = (
                    f"For switch {switch.get('name')} "
                    f"interface {interface.get('name')} "
                )

                pvlan_mode = interface.get('pvlan_mode')
                if pvlan_mode is None:
                    results.append(prefix + "pvlan_mode is required when mode is 'pvlan'.")
                    continue

                # pvlan_association only on host / trunk secondary
                if interface.get('pvlan_association') is not None \
                        and pvlan_mode not in cls.ASSOCIATION_MODES:
                    results.append(
                        prefix + f"pvlan_association is only valid for pvlan_mode "
                        f"'host' or 'trunk secondary', not '{pvlan_mode}'."
                    )

                # pvlan_mapping only on promiscuous / trunk promiscuous
                if interface.get('pvlan_mapping') is not None \
                        and pvlan_mode not in cls.MAPPING_MODES:
                    results.append(
                        prefix + f"pvlan_mapping is only valid for pvlan_mode "
                        f"'promiscuous' or 'trunk promiscuous', not '{pvlan_mode}'."
                    )

                # native_vlan / trunk_allowed_vlans only on trunk submodes
                if interface.get('native_vlan') is not None \
                        and pvlan_mode not in cls.TRUNK_MODES:
                    results.append(
                        prefix + f"native_vlan is only valid for trunk pvlan_mode "
                        f"('trunk promiscuous' or 'trunk secondary'), not '{pvlan_mode}'."
                    )
                if interface.get('trunk_allowed_vlans') is not None \
                        and pvlan_mode not in cls.TRUNK_MODES:
                    results.append(
                        prefix + f"trunk_allowed_vlans is only valid for trunk pvlan_mode "
                        f"('trunk promiscuous' or 'trunk secondary'), not '{pvlan_mode}'."
                    )

        return results

    @classmethod
    def data_model_key_check(cls, tested_object, keys):
        dm_key_dict = {
            'keys_found': [], 'keys_not_found': [],
            'keys_data': [], 'keys_no_data': [],
        }
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

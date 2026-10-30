class Rule:
    id = "318"
    description = "Verify MACsec key chain and policy are set when enable_macsec_interface_policy is true"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        switches_check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' not in switches_check['keys_data']:
            return results

        switches = data_model['vxlan']['topology']['switches']
        for switch in switches:
            for interface in switch.get('interfaces', []):
                policy = interface.get('enable_macsec_interface_policy', None)

                if policy is True:
                    missing = []
                    if not interface.get('macsec_key_chain_name'):
                        missing.append('macsec_key_chain_name')
                    if not interface.get('macsec_policy_name'):
                        missing.append('macsec_policy_name')
                    if missing:
                        results.append(
                            f"For switch {switch.get('name')} "
                            f"interface {interface.get('name')} "
                            f"enable_macsec_interface_policy=true requires: "
                            f"{', '.join(missing)}."
                        )
                else:
                    orphan = []
                    if interface.get('macsec_key_chain_name'):
                        orphan.append('macsec_key_chain_name')
                    if interface.get('macsec_policy_name'):
                        orphan.append('macsec_policy_name')
                    if interface.get('macsec_fallback_key_chain_name'):
                        orphan.append('macsec_fallback_key_chain_name')
                    if orphan:
                        results.append(
                            f"For switch {switch.get('name')} "
                            f"interface {interface.get('name')} "
                            f"MACsec sub-fields ({', '.join(orphan)}) require "
                            f"enable_macsec_interface_policy=true on the same interface."
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

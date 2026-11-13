class Rule:
    id = "407"
    description = (
        "Verify SVIs on non-ToR switches in VXLAN EVPN fabrics use only the "
        "default VRF; a non-default VRF on an SVI is valid only on a ToR switch"
    )
    severity = "HIGH"

    # Fabric types where the VXLAN EVPN SVI/VRF constraint applies.
    EVPN_FABRIC_TYPES = ("VXLAN_EVPN", "eBGP_VXLAN")

    # VRF values that represent the default VRF (an unset vrf omits int_vrf,
    # which NDFC resolves to the default VRF).
    DEFAULT_VRFS = ("", "default")

    @classmethod
    def match(cls, data_model):
        results = []

        fabric_check = cls.data_model_key_check(data_model, ['vxlan', 'fabric', 'type'])
        if 'type' not in fabric_check['keys_found']:
            return results
        if data_model['vxlan']['fabric']['type'] not in cls.EVPN_FABRIC_TYPES:
            return results

        switches_check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' not in switches_check['keys_data']:
            return results
        switches = data_model['vxlan']['topology']['switches']

        tor_names = cls.collect_tor_switch_names(data_model)

        for switch in switches:
            if cls.is_tor(switch, tor_names):
                continue
            for interface in switch.get('interfaces', []):
                if interface.get('mode') != 'vlan':
                    continue
                vrf = interface.get('vrf')
                if vrf is not None and vrf not in cls.DEFAULT_VRFS:
                    results.append(
                        f"For switch {switch.get('name')} SVI {interface.get('name')} "
                        f"uses VRF '{vrf}'. In VXLAN EVPN fabrics, SVIs on non-ToR "
                        f"switches can only be created in the default VRF."
                    )
        return results

    @classmethod
    def is_tor(cls, switch, tor_names):
        return switch.get('role') == 'tor' or switch.get('name') in tor_names

    @classmethod
    def collect_tor_switch_names(cls, data_model):
        tor_names = set()
        topology = data_model.get('vxlan', {}).get('topology', {}) or {}
        for peer in topology.get('tor_peers') or []:
            for key in ('tor1', 'tor2'):
                name = cls._extract_name(peer.get(key))
                if name:
                    tor_names.add(name)
        return tor_names

    @staticmethod
    def _extract_name(value):
        if not value:
            return None
        return value.get('name') if isinstance(value, dict) else value

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

class Rule:
    id = "325"
    description = "Verify DHCP relay configuration: each dhcp_relay_servers entry requires both address and vrf; at most 4 servers are supported"
    severity = "HIGH"

    MAX_SERVERS = 4

    @classmethod
    def match(cls, data_model):
        results = []
        switches_check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' not in switches_check['keys_data']:
            return results

        switches = data_model['vxlan']['topology']['switches']
        for switch in switches:
            for interface in switch.get('interfaces', []):
                servers = interface.get('dhcp_relay_servers')
                if not servers:
                    continue

                # Check 1: at most 4 DHCP relay servers
                if len(servers) > cls.MAX_SERVERS:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"dhcp_relay_servers has {len(servers)} entries; "
                        f"at most {cls.MAX_SERVERS} are supported."
                    )

                # Check 2: each entry requires both address and vrf
                for idx, entry in enumerate(servers, start=1):
                    if not isinstance(entry, dict):
                        continue
                    address = entry.get('ip_address')
                    vrf = entry.get('vrf')
                    if address is None:
                        results.append(
                            f"For switch {switch.get('name')} "
                            f"interface {interface.get('name')} "
                            f"dhcp_relay_servers entry {idx} is missing 'ip_address'."
                        )
                    if vrf is None:
                        results.append(
                            f"For switch {switch.get('name')} "
                            f"interface {interface.get('name')} "
                            f"dhcp_relay_servers entry {idx} is missing 'vrf' "
                            f"(VRF is required for each DHCP relay server)."
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

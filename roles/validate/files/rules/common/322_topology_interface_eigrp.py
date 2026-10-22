class Rule:
    id = "322"
    description = "Verify EIGRP configuration: sub-fields require process tag and enable_eigrp_routing; BFD and IPv4 passive fields are mutually exclusive"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        switches_check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' not in switches_check['keys_data']:
            return results

        # IPv4-only attributes — gated on enable_eigrp_routing=true
        eigrp_ipv4_attributes = [
            'eigrp_no_ipv4_passive', 'eigrp_ipv4_passive',
            'eigrp_ipv4_distribute_list_prefix_list', 'eigrp_ipv4_distribute_list_direction',
        ]
        # IPv6-only attributes — gated on enable_eigrp_ipv6_routing=true
        eigrp_ipv6_attributes = [
            'eigrp_no_ipv6_passive',
            'eigrp_ipv6_distribute_list_prefix_list', 'eigrp_ipv6_distribute_list_direction',
        ]
        # Protocol-agnostic attributes — gated on either routing flag being true
        eigrp_both_attributes = [
            'enable_eigrp_shutdown', 'enable_eigrp_bfd', 'disable_eigrp_bfd',
        ]
        # All EIGRP sub-fields (for the outer process_tag gate check)
        eigrp_sub_fields = [
            'enable_eigrp_routing', 'enable_eigrp_ipv6_routing',
            *eigrp_ipv4_attributes, *eigrp_ipv6_attributes, *eigrp_both_attributes,
        ]

        switches = data_model['vxlan']['topology']['switches']
        for switch in switches:
            for interface in switch.get('interfaces', []):
                tag = interface.get('eigrp_process_tag', None)
                enable_v4 = interface.get('enable_eigrp_routing', None)
                enable_v6 = interface.get('enable_eigrp_ipv6_routing', None)

                sub_set = [f for f in eigrp_sub_fields if interface.get(f) is not None]
                if sub_set and not tag:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"EIGRP sub-fields ({', '.join(sub_set)}) require "
                        f"eigrp_process_tag to be set on the same interface."
                    )

                v4_set = [f for f in eigrp_ipv4_attributes if interface.get(f) is not None]
                if v4_set and enable_v4 is not True:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"EIGRP IPv4 attributes ({', '.join(v4_set)}) require "
                        f"enable_eigrp_routing=true on the same interface."
                    )

                v6_set = [f for f in eigrp_ipv6_attributes if interface.get(f) is not None]
                if v6_set and enable_v6 is not True:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"EIGRP IPv6 attributes ({', '.join(v6_set)}) require "
                        f"enable_eigrp_ipv6_routing=true on the same interface."
                    )

                both_set = [f for f in eigrp_both_attributes if interface.get(f) is not None]
                if both_set and enable_v4 is not True and enable_v6 is not True:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"EIGRP attributes ({', '.join(both_set)}) require "
                        f"enable_eigrp_routing=true or enable_eigrp_ipv6_routing=true on the same interface."
                    )

                if interface.get('enable_eigrp_bfd') is True and interface.get('disable_eigrp_bfd') is True:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"enable_eigrp_bfd and disable_eigrp_bfd cannot both be true "
                        f"on the same interface (mutually exclusive)."
                    )

                if interface.get('eigrp_ipv4_passive') is True and interface.get('eigrp_no_ipv4_passive') is True:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"eigrp_ipv4_passive and eigrp_no_ipv4_passive cannot both be true "
                        f"on the same interface (mutually exclusive)."
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
                    dm_key_dict['keys_not_found'].append(key)
            else:
                dm_key_dict['keys_not_found'].append(key)
        return dm_key_dict

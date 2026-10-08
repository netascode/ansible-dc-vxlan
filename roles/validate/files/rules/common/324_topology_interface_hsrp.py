class Rule:
    id = "324"
    description = "Verify HSRP configuration: sub-fields require enable_hsrp; enable_hsrp requires hsrp_vip, hsrp_group and a primary ipv4_address; \
    preempt-delay requires preempt; forwarding thresholds require hsrp_priority; hsrp_secondary_vips require HSRP and must be in the SVI primary subnet"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        switches_check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' not in switches_check['keys_data']:
            return results

        # Fields that require enable_hsrp=true
        hsrp_sub_fields = [
            'hsrp_vip', 'hsrp_group', 'hsrp_version', 'hsrp_priority', 'preempt',
            'hsrp_vipv6', 'hsrp_groupv6',
            'hsrp_preempt_delay_minimum',
            'hsrp_priority_forwarding_threshold_lower',
            'hsrp_priority_forwarding_threshold_upper',
        ]
        # Fields mandatory when HSRP is enabled
        hsrp_required_fields = ['hsrp_vip', 'hsrp_group']
        # Forwarding-threshold fields require hsrp_priority
        forwarding_threshold_fields = [
            'hsrp_priority_forwarding_threshold_lower',
            'hsrp_priority_forwarding_threshold_upper',
        ]

        switches = data_model['vxlan']['topology']['switches']
        for switch in switches:
            for interface in switch.get('interfaces', []):
                enable_hsrp = interface.get('enable_hsrp', None)

                # Check 1: HSRP sub-fields require enable_hsrp=true
                sub_set = [f for f in hsrp_sub_fields if interface.get(f) is not None]
                if sub_set and enable_hsrp is not True:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"HSRP sub-fields ({', '.join(sub_set)}) require "
                        f"enable_hsrp=true on the same interface."
                    )

                # Check 2: enable_hsrp=true requires hsrp_vip and hsrp_group
                if enable_hsrp is True:
                    missing = [f for f in hsrp_required_fields if interface.get(f) is None]
                    if missing:
                        results.append(
                            f"For switch {switch.get('name')} "
                            f"interface {interface.get('name')} "
                            f"enable_hsrp=true requires ({', '.join(missing)}) "
                            f"to be set on the same interface."
                        )

                    # Check 3: HSRP requires a primary IPv4 address on the SVI
                    if interface.get('ipv4_address') is None:
                        results.append(
                            f"For switch {switch.get('name')} "
                            f"interface {interface.get('name')} "
                            f"enable_hsrp=true requires a primary ipv4_address on the SVI."
                        )

                # Check 4: hsrp_preempt_delay_minimum requires preempt=true
                if interface.get('hsrp_preempt_delay_minimum') is not None \
                        and interface.get('preempt') is not True:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"hsrp_preempt_delay_minimum requires preempt=true "
                        f"on the same interface."
                    )

                # Check 5: forwarding-threshold fields require hsrp_priority
                fwd_set = [f for f in forwarding_threshold_fields if interface.get(f) is not None]
                if fwd_set and interface.get('hsrp_priority') is None:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"HSRP forwarding-threshold fields ({', '.join(fwd_set)}) require "
                        f"hsrp_priority to be set on the same interface."
                    )

                # Check 6: hsrp_secondary_vips require enable_hsrp=true and a primary hsrp_vip,
                #          and each VIP must be in the subnet of the SVI primary address.
                if interface.get('hsrp_secondary_vips'):
                    if enable_hsrp is not True:
                        results.append(
                            f"For switch {switch.get('name')} "
                            f"interface {interface.get('name')} "
                            f"hsrp_secondary_vips require enable_hsrp=true on the same interface."
                        )
                    elif interface.get('hsrp_vip') is None:
                        results.append(
                            f"For switch {switch.get('name')} "
                            f"interface {interface.get('name')} "
                            f"hsrp_secondary_vips require a primary hsrp_vip on the same interface."
                        )

                    primary = interface.get('ipv4_address')
                    if primary:
                        network = cls.ipv4_network(primary)
                        if network is not None:
                            for entry in interface.get('hsrp_secondary_vips'):
                                vip = entry.get('hsrp_secondary_vip') if isinstance(entry, dict) else None
                                if vip and not cls.ip_in_network(vip, network):
                                    results.append(
                                        f"For switch {switch.get('name')} "
                                        f"interface {interface.get('name')} "
                                        f"hsrp_secondary_vip {vip} is not in the subnet of the "
                                        f"SVI primary address {primary}."
                                    )

        return results

    @classmethod
    def ipv4_network(cls, addr):
        # addr like '10.123.1.1/24' -> (network_int, prefix_len); returns None if no prefix
        try:
            if '/' not in addr:
                return None
            ip_str, plen = addr.split('/')
            plen = int(plen)
            octets = [int(o) for o in ip_str.split('.')]
            ip_int = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]
            mask = (0xFFFFFFFF << (32 - plen)) & 0xFFFFFFFF
            return (ip_int & mask, mask)
        except Exception:
            return None

    @classmethod
    def ip_in_network(cls, ip_str, network):
        try:
            net_int, mask = network
            ip_str = ip_str.split('/')[0]
            octets = [int(o) for o in ip_str.split('.')]
            ip_int = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]
            return (ip_int & mask) == net_int
        except Exception:
            return True  # fail open on parse error; schema validates address format

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

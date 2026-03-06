class Rule:
    id = "205"
    description = "Verify fabric underlay IPv6 mutually exclusive parameters"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []

        enable_ipv6_underlay_keys = ['vxlan', 'underlay', 'general', 'enable_ipv6_underlay']
        check = cls.data_model_key_check(data_model, enable_ipv6_underlay_keys)
        if (
            ('enable_ipv6_underlay' in check['keys_found']) and
            ('enable_ipv6_underlay' in check['keys_data'])
        ):
            enable_ipv6_underlay = data_model["vxlan"]["underlay"]["general"]["enable_ipv6_underlay"]

            # Check if IPv6 is enabled and if so, ensure BFD settings are not configured
            for item in ['enable', 'ospf', 'isis', 'ibgp', 'pim']:
                underlay_bfd_keys = ['vxlan', 'underlay', 'bfd', item]
                check = cls.data_model_key_check(data_model, underlay_bfd_keys)
                if (
                    ('bfd' in check['keys_found']) and
                    (item in check['keys_found']) and
                    (item in check['keys_data']) and
                    (enable_ipv6_underlay)
                ):
                    results.append(
                        f"vxlan.underlay.bfd.{item} should not be configured when "
                        "vxlan.underlay.general.enable_ipv6_underlay is configured as true. "
                    )

                    return results

            netflow_keys = ['vxlan', 'global', 'ibgp']
            check = cls.data_model_key_check(data_model, netflow_keys)
            if 'ibgp' in check['keys_found']:
                netflow_keys = ['vxlan', 'global', 'ibgp', 'netflow', 'enable']
                check = cls.data_model_key_check(data_model, netflow_keys)

            if 'ibgp' in check['keys_not_found'] or 'netflow' in check['keys_not_found']:
                netflow_keys = ['vxlan', 'global', 'netflow', 'enable']
                check = cls.data_model_key_check(data_model, netflow_keys)

            if (
                ('netflow' in check['keys_found']) and
                ('enable' in check['keys_found']) and
                ('enable' in check['keys_data']) and
                (enable_ipv6_underlay)
            ):
                results.append(
                    "vxlan.global.ibgp.netflow.enable should not be configured when "
                    "vxlan.underlay.general.enable_ipv6_underlay is configured as true. "
                )

                return results

        ipv6_link_local_keys = ['vxlan', 'underlay', 'ipv6', 'enable_ipv6_link_local_address']
        check = cls.data_model_key_check(data_model, ipv6_link_local_keys)
        if (
            ('enable_ipv6_link_local_address' in check['keys_found']) and
            ('enable_ipv6_link_local_address' in check['keys_data'])
        ):
            enable_ipv6_link_local_address = data_model["vxlan"]["underlay"]["ipv6"]["enable_ipv6_link_local_address"]

            # Check if IPv6 link local address is enabled and if so, ensure IPv6 subnet mask is not configured
            ipv6_subnet_mask_keys = ['vxlan', 'underlay', 'ipv6', 'underlay_subnet_mask']
            check = cls.data_model_key_check(data_model, ipv6_subnet_mask_keys)
            if (
                ('underlay_subnet_mask' in check['keys_found']) and
                ('underlay_subnet_mask' in check['keys_data']) and
                (enable_ipv6_link_local_address)
            ):
                results.append(
                    "vxlan.underlay.ipv6.underlay_subnet_mask should not be configured when "
                    "vxlan.underlay.ipv6.enable_ipv6_link_local_address is configured as true."
                )

                return results

            # Check if IPv6 link local address is enabled and if so, ensure IPv6 subnet IP range is not configured
            ipv6_subnet_ip_range_keys = ['vxlan', 'underlay', 'ipv6', 'underlay_subnet_ip_range']
            check = cls.data_model_key_check(data_model, ipv6_subnet_ip_range_keys)
            if (
                ('underlay_subnet_ip_range' in check['keys_found']) and
                ('underlay_subnet_ip_range' in check['keys_data']) and
                (enable_ipv6_link_local_address)
            ):
                results.append(
                    "vxlan.underlay.ipv6.underlay_subnet_ip_range should not be configured when "
                    "vxlan.underlay.ipv6.enable_ipv6_link_local_address is configured as true."
                )

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

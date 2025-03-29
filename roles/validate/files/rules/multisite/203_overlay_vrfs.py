class Rule:
    id = "203"
    description = "Verify VRF attributes are set for multisite overlay vs standalone fabric overlay"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        child_fabric_attributes = [
            'adv_host_routes',
            'adv_default_routes',
            'static_default_route',
            'bgp_password',
            'bgp_password_encryption_type',
            'netflow_enable',
            'netflow_monitor',
            'trm_enable',
            'trm_bgw_msite',
            'no_rp',
            'rp_external',
            'rp_address',
            'rp_loopback_id',
            'underlay_mcast_ip',
            'overlay_multicast_group',
            'import_mvpn_rt',
            'export_mvpn_rt'
        ]

        vrf_keys = ['vxlan', 'multisite', 'overlay', 'vrfs']
        check = cls.data_model_key_check(inventory, vrf_keys)
        if 'vrfs' in check['keys_found'] and 'vrfs' in check['keys_data']:
            vrfs = inventory['vxlan']['multisite']['overlay']['vrfs']
            for vrf in vrfs:
                for attr in vrf:
                    if attr in child_fabric_attributes:
                        results.append(
                            f"When in a Multisite fabric, vxlan.multisite.overlay.vrfs "
                            f"item vrf {vrf['name']} with attribute {attr} must be "
                            f"defined under vxlan.multisite.overlay.vrfs item vrf {vrf['name']} "
                            "under attribute child_fabrics."
                        )

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

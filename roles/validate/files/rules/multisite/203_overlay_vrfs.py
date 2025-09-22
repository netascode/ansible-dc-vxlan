class Rule:
    id = "203"
    description = "Verify VRF attributes are set for multisite overlay vs standalone fabric overlay"
    severity = "HIGH"

    msg = "VRF {0} attribute '{1}' must be defined under vxlan.multisite.overlay.vrfs under the 'child_fabrics:' key."

    @classmethod
    def match(cls, data_model):
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
        check = cls.data_model_key_check(data_model, vrf_keys)
        if 'vrfs' in check['keys_found'] and 'vrfs' in check['keys_data']:
            vrfs = data_model['vxlan']['multisite']['overlay']['vrfs']
            for vrf in vrfs:
                for attr in vrf:
                    if attr in child_fabric_attributes:
                        results.append(cls.msg.format(vrf['name'], attr))

                for child_fabric in vrf.get('child_fabrics', []):
                    if not child_fabric.get('netflow_enable') and child_fabric.get('netflow_monitor'):
                        results.append(
                            f"VRF {vrf['name']} attribute 'netflow_monitor' can only be defined if 'netflow_enable' is true under the 'child_fabrics:' key."
                        )

                    current_vrf_trm_no_rp = child_fabric.get("no_rp")
                    current_vrf_trm_rp_external = child_fabric.get("rp_external")
                    current_vrf_trm_rp_address = child_fabric.get("rp_address")
                    current_vrf_trm_rp_loopback_id = child_fabric.get("rp_loopback_id")
                    current_vrf_trm_underlay_mcast_ip = child_fabric.get("underlay_mcast_ip")
                    current_vrf_trm_overlay_multicast_group = child_fabric.get("overlay_multicast_group")

                    # import epdb; epdb.st()

                    if child_fabric.get('trm_enable'):
                        if (
                            not current_vrf_trm_no_rp and
                            not current_vrf_trm_rp_external and
                            (
                                current_vrf_trm_rp_address is None or
                                current_vrf_trm_rp_loopback_id is None or
                                current_vrf_trm_underlay_mcast_ip is None
                            )
                        ):
                            results.append(
                                f"When VRF {vrf['name']} child_fabric attribute no_rp or rp_external is disabled (false), "
                                "then the attributes rp_address, rp_loopback_id, underlay_mcast_ip must be set."
                            )
                            break

                        if current_vrf_trm_no_rp and current_vrf_trm_underlay_mcast_ip is None:
                            results.append(
                                f"When VRF {vrf['name']} child_fabric attribute no_rp is enabled (true), "
                                "then the attribute underlay_mcast_ip must be set."
                            )
                            break

                        if (
                            current_vrf_trm_no_rp and current_vrf_trm_rp_external or
                            current_vrf_trm_no_rp and current_vrf_trm_rp_address or
                            current_vrf_trm_no_rp and current_vrf_trm_rp_loopback_id or
                            current_vrf_trm_no_rp and current_vrf_trm_overlay_multicast_group
                        ):
                            results.append(
                                f"When VRF {vrf['name']} attribute no_rp is enabled (true), "
                                "then attributes rp_external, rp_address, rp_loopback_id, overlay_multicast_group must be disabled (false)."
                            )
                            break

                        if current_vrf_trm_rp_external and current_vrf_trm_rp_loopback_id:
                            results.append(
                                f"When VRF {vrf['name']} attribute rp_external is enabled (true), "
                                "then the attribute rp_loopback_id must be disabled (false)."
                            )
                            break

                        if (current_vrf_trm_rp_external and current_vrf_trm_rp_address is None or
                                current_vrf_trm_rp_external and current_vrf_trm_underlay_mcast_ip is None):
                            results.append(
                                f"When VRFs {vrf['name']} attribute rp_external is enabled (true), "
                                "attributes rp_address and underlay_mcast_ip must be set."
                            )
                            break

                    if not child_fabric.get('trm_enable'):
                        if child_fabric.get('trm_bgw_msite'):
                            results.append(
                                f"When VRFs {vrf['name']} attribute trm_bgw_msite is enabled (true), "
                                "attribute trm_enable must be enabled (true)."
                            )
                            break

                        if child_fabric.get('import_mvpn_rt') or child_fabric.get('export_mvpn_rt'):
                            results.append(
                                f"When VRFs {vrf['name']} attribute import_mvpn_rt or export_mvpn_rt is enabled (true), "
                                "attribute trm_enable must be enabled (true)."
                            )
                            break

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

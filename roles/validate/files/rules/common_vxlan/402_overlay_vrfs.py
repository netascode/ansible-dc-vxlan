class Rule:
    id = "402"
    description = "Verify VRF elements are enabled in fabric overlay services"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        fabric_netflow_status = False
        fabric_trm_status = False
        vrfs = []

        if data_model.get("vxlan", None):
            if data_model["vxlan"].get("global", None):
                if data_model["vxlan"].get("global").get("netflow", None):
                    fabric_netflow_status = data_model["vxlan"]["global"]["netflow"].get("enable", False)

            if data_model["vxlan"].get("underlay", None):
                if data_model["vxlan"].get("underlay").get("multicast", None):
                    if data_model["vxlan"].get("underlay").get("multicast").get("ipv4", None):
                        fabric_trm_status = data_model["vxlan"]["underlay"]["multicast"]["ipv4"].get("trm_enable", False)

            vrf_keys = ['vxlan', 'overlay', 'vrfs']
            check = cls.data_model_key_check(data_model, vrf_keys)
            if 'vrfs' in check['keys_data']:
                vrfs = data_model["vxlan"]["overlay"]["vrfs"]
            else:
                vrf_keys = ['vxlan', 'overlay_services', 'vrfs']
                check = cls.data_model_key_check(data_model, vrf_keys)
                if 'vrfs' in check['keys_data']:
                    vrfs = data_model["vxlan"]["overlay_services"]["vrfs"]

        for vrf in vrfs:
            current_vrf_netflow_status = vrf.get("netflow_enable", None)
            if current_vrf_netflow_status is not None:
                if fabric_netflow_status is False and current_vrf_netflow_status is True:
                    results.append(
                        f"For vxlan.overlay.vrfs.{vrf['name']}.netflow_enable to be enabled, "
                        f"first vxlan.global.netflow.enable must be enabled (true)."
                    )
                    break

                if fabric_netflow_status and current_vrf_netflow_status:
                    current_vrf_netflow_monitor = vrf.get("netflow_monitor", None)
                    if current_vrf_netflow_monitor is None:
                        results.append(
                            f"When vxlan.overlay.vrfs.{vrf['name']}.netflow_enable is enabled, "
                            f"then vxlan.overlay.vrfs.{vrf['name']}.netflow_monitor must be set "
                            "to a valid value from vxlan.global.netflow."
                        )
                        break

            current_vrf_trm_status = vrf.get("trm_enable", None)
            if current_vrf_trm_status is not None:
                if fabric_trm_status is False and current_vrf_trm_status is True:
                    results.append(
                        f"For vxlan.overlay.vrfs.{vrf['name']}.trm_enable to be enabled, "
                        f"first vxlan.underlay.multicast.ipv4.trm_enable must be enabled (true)."
                    )
                    break

                current_vrf_trm_no_rp = vrf.get("no_rp", None)
                current_vrf_trm_rp_external = vrf.get("rp_external", None)
                current_vrf_trm_rp_address = vrf.get("rp_address", None)
                current_vrf_trm_rp_loopback_id = vrf.get("rp_loopback_id", None)
                current_vrf_trm_underlay_mcast_ip = vrf.get("underlay_mcast_ip", None)
                current_vrf_trm_overlay_multicast_group = vrf.get("overlay_multicast_group", None)

                if fabric_trm_status:
                    if current_vrf_trm_no_rp and current_vrf_trm_underlay_mcast_ip is None:
                        results.append(
                            f"When vxlan.overlay.vrfs.{vrf['name']}.no_rp is enabled (true), "
                            f"then vxlan.overlay.vrfs.{vrf['name']}.underlay_mcast_ip must be set."
                        )
                        break

                    if (current_vrf_trm_no_rp and current_vrf_trm_rp_external or
                            current_vrf_trm_no_rp and current_vrf_trm_rp_address or
                            current_vrf_trm_no_rp and current_vrf_trm_rp_loopback_id or
                            current_vrf_trm_no_rp and current_vrf_trm_overlay_multicast_group):
                        results.append(
                            f"When vxlan.overlay.vrfs.{vrf['name']}.no_rp is enabled (true), "
                            f"then vxlan.overlay.vrfs.{vrf['name']}.rp_external, "
                            f"vxlan.overlay.vrfs.{vrf['name']}.rp_address, "
                            f"vxlan.overlay.vrfs.{vrf['name']}.rp_loopback_id, "
                            f"vxlan.overlay.vrfs.{vrf['name']}.overlay_multicast_group must be disabled (false)."
                        )
                        break

                    if current_vrf_trm_rp_external and current_vrf_trm_rp_loopback_id:
                        results.append(
                            f"When vxlan.overlay.vrfs.{vrf['name']}.rp_external is enabled (true), "
                            f"then vxlan.overlay.vrfs.{vrf['name']}.rp_loopback_id must be disabled (false)."
                        )
                        break

                    if (current_vrf_trm_rp_external and current_vrf_trm_rp_address is None or
                            current_vrf_trm_rp_external and current_vrf_trm_underlay_mcast_ip is None):
                        results.append(
                            f"When vxlan.overlay.vrfs.{vrf['name']}.rp_external is enabled (true), "
                            f"then vxlan.overlay.vrfs.{vrf['name']}.rp_address and "
                            f"vxlan.overlay.vrfs.{vrf['name']}.underlay_mcast_ip must be set."
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

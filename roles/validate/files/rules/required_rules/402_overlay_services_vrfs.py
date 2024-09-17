class Rule:
    id = "402"
    description = "Verify VRF elements are enabled in fabric overlay services"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        fabric_netflow_status = False
        fabric_trm_status = False
        vrfs = []

        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("global", None):
                if inventory["vxlan"].get("global").get("netflow", None):
                    fabric_netflow_status = inventory["vxlan"]["global"]["netflow"].get("enable", False)

            if inventory["vxlan"].get("underlay", None):
                if inventory["vxlan"].get("underlay").get("multicast", None):
                    fabric_trm_status = inventory["vxlan"]["underlay"]["multicast"].get("trm_enable", False)

            if inventory["vxlan"].get("overlay_services", None):
                if inventory["vxlan"].get("overlay_services").get("vrfs", None):
                    vrfs = inventory["vxlan"]["overlay_services"]["vrfs"]

        for vrf in vrfs:
            current_vrf_netflow_status = vrf.get("netflow_enable", None)
            if current_vrf_netflow_status is not None:
                if fabric_netflow_status is False and current_vrf_netflow_status is True:
                    results.append(
                        f"For vxlan.overlay_services.vrfs.{vrf['name']}.netflow_enable to be enabled, "
                        f"first vxlan.global.netflow.enable must be enabled (true)."
                    )
                    break

                if fabric_netflow_status and current_vrf_netflow_status:
                    current_vrf_netflow_monitor = vrf.get("netflow_monitor", None)
                    if current_vrf_netflow_monitor is None:
                        results.append(
                            f"When vxlan.overlay_services.vrfs.{vrf['name']}.netflow_enable is enabled, "
                            f"then vxlan.overlay_services.vrfs.{vrf['name']}.netflow_monitor must be set "
                            "to a valid value from vxlan.global.netflow."
                        )
                        break

            current_vrf_trm_status = vrf.get("trm_enable", None)
            if current_vrf_trm_status is not None:
                if fabric_trm_status is False and current_vrf_trm_status is True:
                    results.append(
                        f"For vxlan.overlay_services.vrfs.{vrf['name']}.trm_enable to be enabled, "
                        f"first vxlan.underlay.multicast.trm_enable must be enabled (true)."
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
                            f"When vxlan.overlay_services.vrfs.{vrf['name']}.no_rp is enabled (true), "
                            f"then vxlan.overlay_services.vrfs.{vrf['name']}.underlay_mcast_ip must be set."
                        )
                        break

                    if (current_vrf_trm_no_rp and current_vrf_trm_rp_external or
                            current_vrf_trm_no_rp and current_vrf_trm_rp_address or
                            current_vrf_trm_no_rp and current_vrf_trm_rp_loopback_id or
                            current_vrf_trm_no_rp and current_vrf_trm_overlay_multicast_group):
                        results.append(
                            f"When vxlan.overlay_services.vrfs.{vrf['name']}.no_rp is enabled (true), "
                            f"then vxlan.overlay_services.vrfs.{vrf['name']}.rp_external, "
                            f"vxlan.overlay_services.vrfs.{vrf['name']}.rp_address, "
                            f"vxlan.overlay_services.vrfs.{vrf['name']}.rp_loopback_id, "
                            f"vxlan.overlay_services.vrfs.{vrf['name']}.overlay_multicast_group must be disabled (false)."
                        )
                        break

                    if current_vrf_trm_rp_external and current_vrf_trm_rp_loopback_id:
                        results.append(
                            f"When vxlan.overlay_services.vrfs.{vrf['name']}.rp_external is enabled (true), "
                            f"then vxlan.overlay_services.vrfs.{vrf['name']}.rp_loopback_id must be disabled (false)."
                        )
                        break

                    if (current_vrf_trm_rp_external and current_vrf_trm_rp_address is None or
                            current_vrf_trm_rp_external and current_vrf_trm_underlay_mcast_ip is None):
                        results.append(
                            f"When vxlan.overlay_services.vrfs.{vrf['name']}.rp_external is enabled (true), "
                            f"then vxlan.overlay_services.vrfs.{vrf['name']}.rp_address and "
                            f"vxlan.overlay_services.vrfs.{vrf['name']}.underlay_mcast_ip must be set."
                        )
                        break

        return results
# if inventory["vxlan"].get("policy").get("switches", None):
#     switches = inventory["vxlan"]["policy"]["switches"]

#     if inventory.get("vxlan"):
#         if inventory["vxlan"].get("topology"):
#             if inventory.get("vxlan").get("topology").get("switches"):
#                 topology_switches = inventory.get("vxlan").get("topology").get("switches")
#     for switch in switches:
#         if not ((any(topology_switch['name'] == switch['name'] for topology_switch in topology_switches)) or
#                 (any(topology_switch['management'].get('management_ipv4_address', None) == switch['name']
#                         for topology_switch in topology_switches)) or
#                 (any(topology_switch['management'].get('management_ipv6_address', None) == switch['name']
#                         for topology_switch in topology_switches))):
#             results.append(
#                 f"Switch name {switch['name']} is defined and must be defined in the topology switches section."
#             )
#             break
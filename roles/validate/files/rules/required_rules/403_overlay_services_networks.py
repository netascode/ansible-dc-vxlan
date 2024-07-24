class Rule:
    id = "403"
    description = "Verify Network elements are enabled in fabric overlay services"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        fabric_netflow_status = False
        fabric_trm_status = False
        networks = []

        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("global", None):
                if inventory["vxlan"].get("global").get("netflow", None):
                    fabric_netflow_status = inventory["vxlan"]["global"]["netflow"].get("enable", False)

        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("underlay", None):
                if inventory["vxlan"].get("underlay").get("multicast", None):
                    fabric_trm_status = inventory["vxlan"]["underlay"]["multicast"].get("trm_enable", False)

        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("overlay_services", None):
                if inventory["vxlan"].get("overlay_services").get("networks", None):
                    networks = inventory["vxlan"]["overlay_services"]["networks"]

        for network in networks:
            current_network_netflow_status = network.get("netflow_enable", None)
            if current_network_netflow_status is not None:
                if fabric_netflow_status is False and current_network_netflow_status is True:
                    results.append(
                        f"For vxlan.overlay_services.networks.{network['name']}.netflow_enable to be enabled, "
                        f"first vxlan.global.netflow.enable must be enabled (true)."
                    )

            current_network_trm_status = network.get("trm_enable", None)
            if current_network_trm_status is not None:
                if fabric_trm_status is False and current_network_trm_status is True:
                    results.append(
                        f"For vxlan.overlay_services.networks.{network['name']}.trm_enable to be enabled, "
                        f"first vxlan.underlay.multicast.trm_enable must be enabled (true)."
                    )

        return results

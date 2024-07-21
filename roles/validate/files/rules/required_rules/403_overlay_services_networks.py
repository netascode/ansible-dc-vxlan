class Rule:
    id = "403"
    description = "Verify Network elements are enabled in fabric overlay services"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        netflow_status = False
        networks = []

        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("global", None):
                if inventory["vxlan"].get("global").get("netflow", None):
                    netflow_status = inventory["vxlan"]["global"]["netflow"].get("enable", False)

        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("overlay_services", None):
                if inventory["vxlan"].get("overlay_services").get("networks", None):
                    networks = inventory["vxlan"]["overlay_services"]["networks"]

        for network in networks:
            current_network_netflow_status = network.get("netflow_enable", False)
            if current_network_netflow_status != netflow_status:
                results.append(
                    f"For vxlan.overlay_services.networks.{network['name']}.netflow_enable to be enabled, "
                    f"first vxlan.global.netflow.enable must be enabled (true)."
                )

        return results

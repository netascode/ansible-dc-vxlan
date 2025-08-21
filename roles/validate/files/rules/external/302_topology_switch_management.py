class Rule:
    id = "302"
    description = "Verify at least either a mgmt IPv4 or IPv6 address is configured"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        management_defined = []
        switches = []
        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("topology", None):
                if inventory.get("vxlan").get("topology").get("switches", None):
                    switches = inventory.get("vxlan").get("topology").get("switches")
        for switch in switches:
            if not switch.get("management", False):
                results.append(
                    f"vxlan.topology.switches.{switch['name']}.management must be defined"
                )
            else:
                management_defined.append(switch)

        for switch in management_defined:
            if not (
                switch["management"].get("management_ipv4_address", False)
                or switch["management"].get("management_ipv6_address", False)
            ):
                results.append(
                    f"vxlan.topology.switches.{switch['name']}.management "
                    f"must define either management_ipv4_address or management_ipv6_address"
                )
        return results

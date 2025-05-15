class Rule:
    id = "307"
    description = "Verify subnet is defined when preprovision is set"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        switches = []
        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("topology", None):
                if inventory.get("vxlan").get("topology").get("switches", None):
                    switches = inventory.get("vxlan").get("topology").get("switches")
        for switch in switches:
            if switch.get("poap").get("preprovision", None):
                if not switch.get("management").get("subnet_mask_ipv4"):
                    results.append(
                        f"vxlan.topology.switches.{switch['name']}.subnet_mask_ipv4 must be defined when preprovision is used."
                    )
        return results

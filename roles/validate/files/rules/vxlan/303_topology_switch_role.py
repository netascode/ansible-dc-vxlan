class Rule:
    id = "303"
    description = "Verify switch role is defined"
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
            if not switch.get("role", False):
                results.append(
                    f"vxlan.topology.switches.{switch['name']}.role must be defined"
                )
        return results

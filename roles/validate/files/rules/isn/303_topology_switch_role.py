class Rule:
    id = "303"
    description = "Verify switch role is defined"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        switches = []
        if data_model.get("vxlan", None):
            if data_model["vxlan"].get("topology", None):
                if data_model.get("vxlan").get("topology").get("switches", None):
                    switches = data_model.get("vxlan").get("topology").get("switches")
        for switch in switches:
            if not switch.get("role", False):
                results.append(
                    f"vxlan.topology.switches.{switch['name']}.role must be defined"
                )
        return results

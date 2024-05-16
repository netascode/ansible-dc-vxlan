class Rule:
    id = "301"
    description = "Verify a switch's serial number exists in the topology inventory"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        switches = []
        if inventory.get("vxlan"):
            if inventory["vxlan"].get("topology"):
                if inventory.get("vxlan").get("topology").get("switches"):
                    switches = inventory.get("vxlan").get("topology").get("switches")
        for switch in switches:
            if not switch.get("serial_number", False):
                results.append(
                    f"vxlan.topology.switches.{switch['name']} serial number must be defined at least once in the topology inventory."
                )

        return results

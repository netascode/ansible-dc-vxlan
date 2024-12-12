class Rule:
    id = "201"
    description = "Verify a spanning tree protocol mutually exclusive parameters."
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("global", None):
                if inventory["vxlan"].get("global", None).get("spanning_tree", None):
                    root_bridge_protocol = inventory["vxlan"]["global"]["spanning_tree"].get("root_bridge_protocol", None)
                    vlan_range = inventory["vxlan"]["global"]["spanning_tree"].get("vlan_range", None)
                    mst_instance_range = inventory["vxlan"]["global"]["spanning_tree"].get("mst_instance_range", None)

                    if vlan_range and mst_instance_range:
                        results.append(
                            "vxlan.global.spanning_tree.vlan_range and vxlan.global.spanning_tree.mst_instance_range "
                            "both cannot be configured at the same time. Please choose one depending on the "
                            "vxlan.global.spanning_tree.root_bridge_protocol selected."
                        )

        return results

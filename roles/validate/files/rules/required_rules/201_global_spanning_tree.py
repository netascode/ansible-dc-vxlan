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
                    mst_instance_range = inventory["vxlan"]["global"]["spanning_tree"].get("vlan_range", None)

                    if root_bridge_protocol == "rpvst+" and not mst_instance_range:
                        results.append(
                            "vxlan.global.spanning_tree.vlan_range must be set when the "
                            "spanning tree vxlan.global.spanning_tree.root_bridge_protocol is set to rpvst+."
                        )

                    if root_bridge_protocol == "mst" and not vlan_range:
                        results.append(
                            "vxlan.global.spanning_tree.mst_instance_range can only be used when the "
                            "spanning tree vxlan.global.spanning_tree.root_bridge_protocol is set to mst."
                        )

        return results

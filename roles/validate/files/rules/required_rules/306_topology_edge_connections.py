class Rule:
    id = "306"
    description = "Verify a switch exists in topology switches if it is refenced in an edge connection."
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        switches = []
        edge_connections = []
        found_edge_connections = []
        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("topology", None):
                if inventory.get("vxlan").get("topology").get("switches", None):
                    switches = inventory.get("vxlan").get("topology").get("switches")
        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("topology", None):
                if inventory.get("vxlan").get("topology").get("edge_connections", None):
                    edge_connections = inventory.get("vxlan").get("topology").get("edge_connections")
        for edge_connection in edge_connections:
            for switch in switches:
                if edge_connection.get("source_device") == switch.get("name"):
                    found_edge_connections.append(edge_connection)
                    break
        if len([_dict for _dict in edge_connections if _dict not in found_edge_connections]) != 0:

        # [_dict for _dict in edge_connections if _dict not in found_edge_connections]
            results.append("the follow edge connections have a source device which isn' tis topology.switches "+ str([_dict for _dict in edge_connections if _dict not in found_edge_connections]))
            #     f"vxlan.topology.edge_connections.{found_edge_connection["source_device"]} "
            #     f"references a switch that does not exist in vxlan.topology.switches"
            # )
        return results
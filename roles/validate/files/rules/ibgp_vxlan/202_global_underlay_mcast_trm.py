class Rule:
    id = "202"
    description = "Verify Fabric Underlay Supports Multicast for TRM"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        fabric_replication = False
        fabric_mcast_mode = False
        fabric_trm = False

        if data_model.get("vxlan", None):
            if data_model["vxlan"].get("underlay", None):
                if data_model["vxlan"].get("underlay").get("general", None):
                    fabric_replication = data_model["vxlan"]["underlay"]["general"].get("replication_mode", False)

                if data_model["vxlan"].get("underlay").get("multicast", None):
                    fabric_mcast_mode = data_model["vxlan"]["underlay"]["multicast"].get("rp_mode", False)
                    fabric_trm = data_model["vxlan"]["underlay"]["multicast"].get("trm_enable", False)

        if fabric_replication:
            if ((fabric_replication == "multicast" and fabric_mcast_mode == "bidir" and fabric_trm) or
                    (fabric_replication == "ingress" and fabric_trm)):
                results.append(
                    "For vxlan.underlay.multicast.trm_enable to be enabled, "
                    "vxlan.underlay.general.replication_mode must be set to multicast and "
                    "vxlan.underlay.multicast.rp_mode must be set to asm."
                )

        return results

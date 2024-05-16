class Rule:
    id = "304"
    description = "Cross Reference VRFs with Networks in the Service Model"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        # Cross Reference Service Model VRFs with Service Model Networks and generate
        # an error message if a network is found that is referencing a VRF
        sm_networks = []
        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("overlay_services", None):
                if inventory.get("vxlan").get("overlay_services").get("networks", None):
                    sm_networks = inventory.get("vxlan").get("overlay_services").get("networks")

        sm_vrfs = []
        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("overlay_services", None):
                if inventory.get("vxlan").get("overlay_services").get("vrfs", None):
                    sm_vrfs = inventory.get("vxlan").get("overlay_services").get("vrfs")
        # Build list of VRF names from sm_networks
        # network_vrf_names = []
        # for net in sm_networks:
        #     if net.get('vrf_name') is not None:
        #         network_vrf_names.append(net.get('vrf_name'))
        # Build list of VRF names from sm_vrfs
        if sm_vrfs and sm_networks:
            vrf_names = []
            for vrf in sm_vrfs:
                vrf_names.append(vrf.get("name"))
            # Compare the two lists and generate an error message if a network is found
            # in network_vrf_names that is not in vrf_names
            for net in sm_networks:
                if net.get("vrf_name") is not None:
                    if net.get("vrf_name") not in vrf_names:
                        # results['failed'] = True
                        results.append(
                            "Network ({0}) is referencing VRF ({1})".format(
                                net.get("name"), net.get("vrf_name")
                            )
                        )
                        results.append(
                            " which is not defined in the service model.  Add the VRF to the service model or remove the network from the service model"
                        )
                        results.append(" and re-run the playbook")

        return results

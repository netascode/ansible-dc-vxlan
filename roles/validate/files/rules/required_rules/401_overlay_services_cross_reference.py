class Rule:
    id = "401"
    description = "Cross Reference VRFs and Networks items in the Service Model"
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

        # Cross reference VRF attach groups hostnames with inventory topology switch names
        vrf_attach_groups = []
        switches = []
        if inventory.get("vxlan"):
            if inventory.get("vxlan").get("overlay_services"):
                if inventory.get("vxlan").get("overlay_services").get("vrf_attach_groups"):
                    vrf_attach_groups = inventory.get("vxlan").get("overlay_services").get("vrf_attach_groups")
                if inventory.get("vxlan").get("topology"):
                    if inventory.get("vxlan").get("topology").get("switches"):
                        switches = inventory.get("vxlan").get("topology").get("switches")
        for vrf_attach_group in vrf_attach_groups:
            for switch in vrf_attach_group.get("switches"):
                if switch.get("hostname"):
                    if len(switches) > 0:
                        if not any(s.get("name") == switch.get("hostname") for s in switches):
                            if not any(s.get('management').get('management_ipv4_address') == switch.get("hostname") for s in switches):
                                if not any(s.get('management').get('management_ipv6_address') == switch.get("hostname") for s in switches):
                                    vag = vrf_attach_group.get("name")
                                    hn = switch.get("hostname")
                                    results.append("VRF attach group {0} hostname {1} does not match any switch in the topology".format(vag, hn))

        # Cross reference Network attach groups hostnames with inventory topology switch names
        network_attach_groups = []
        if inventory.get("vxlan"):
            if inventory.get("vxlan").get("overlay_services"):
                if inventory.get("vxlan").get("overlay_services").get("network_attach_groups"):
                    network_attach_groups = inventory.get("vxlan").get("overlay_services").get("network_attach_groups")
                if inventory.get("vxlan").get("topology"):
                    if inventory.get("vxlan").get("topology").get("switches"):
                        switches = inventory.get("vxlan").get("topology").get("switches")
        for network_attach_group in network_attach_groups:
            for switch in network_attach_group.get("switches"):
                if switch.get("hostname"):
                    if len(switches) > 0:
                        if not any(s.get("name") == switch.get("hostname") for s in switches):
                            if not any(s.get('management').get('management_ipv4_address') == switch.get("hostname") for s in switches):
                                if not any(s.get('management').get('management_ipv6_address') == switch.get("hostname") for s in switches):
                                    nag = network_attach_group.get("name")
                                    hn = switch.get("hostname")
                                    results.append("Network attach group {0} hostname {1} does not match any switch in the topology".format(nag, hn))

        return results

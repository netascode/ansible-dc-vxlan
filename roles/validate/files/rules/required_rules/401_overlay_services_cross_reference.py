class Rule:
    id = "401"
    description = "Cross Reference VRFs and Networks items in the Service Model"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        # Cross Reference Service Model VRFs with Service Model Networks and generate
        # an error message if a network is found that is referencing a VRF

        # Check if vrfs, network and switch data is defined in the service model
        switches = []
        check = cls.data_model_key_check(inventory, ['vxlan', 'topology', 'switches'])
        if 'switches' in check['keys_data']:
            switches = inventory.get("vxlan").get("topology").get("switches")
        if not switches:
            # No switches defined in the service model, no reason to continue
            return results

        sm_networks = []
        check = cls.data_model_key_check(inventory, ['vxlan', 'overlay_services', 'networks'])
        if 'networks' in check['keys_data']:
            sm_networks = inventory.get("vxlan").get("overlay_services").get("networks")

        sm_vrfs = []
        check = cls.data_model_key_check(inventory, ['vxlan', 'overlay_services', 'vrfs'])
        if 'vrfs' in check['keys_data']:
            sm_vrfs = inventory.get("vxlan").get("overlay_services").get("vrfs")

        vrf_attach_groups = []
        check = cls.data_model_key_check(inventory, ['vxlan', 'overlay_services', 'vrf_attach_groups'])
        if 'vrf_attach_groups' in check['keys_data']:
            vrf_attach_groups = inventory.get("vxlan").get("overlay_services").get("vrf_attach_groups")

        network_attach_groups = []
        check = cls.data_model_key_check(inventory, ['vxlan', 'overlay_services', 'network_attach_groups'])
        if 'network_attach_groups' in check['keys_data']:
            network_attach_groups = inventory.get("vxlan").get("overlay_services").get("network_attach_groups")

        # Ensure Network is not referencing a VRF that is not defined in the service model
        results = cls.cross_reference_vrfs_nets(sm_vrfs, sm_networks, results)

        if sm_vrfs and vrf_attach_groups:
            results = cls.cross_reference_switches(vrf_attach_groups, switches, 'vrf', results)
        if sm_networks and network_attach_groups:
            results = cls.cross_reference_switches(network_attach_groups, switches, 'vrf', results)

        return results

    @classmethod
    def data_model_key_check(cls, tested_object, keys):
        dm_key_dict = {'keys_found': [], 'keys_not_found': [], 'keys_data': [], 'keys_no_data': []}
        for key in keys:
            if tested_object and key in tested_object:
                dm_key_dict['keys_found'].append(key)
                tested_object = tested_object[key]
                if tested_object:
                    dm_key_dict['keys_data'].append(key)
                else:
                    dm_key_dict['keys_no_data'].append(key)
            else:
                dm_key_dict['keys_not_found'].append(key)
        return dm_key_dict

    @classmethod
    def cross_reference_vrfs_nets(cls, sm_vrfs, sm_networks, results):
        if not sm_vrfs or not sm_networks:
            return results

        vrf_names = []
        for vrf in sm_vrfs:
            vrf_names.append(vrf.get("name"))
        # Compare the two lists and generate an error message if a network is found
        # in network_vrf_names that is not in vrf_names
        for net in sm_networks:
            if net.get("vrf_name") is not None:
                if net.get("vrf_name") not in vrf_names:
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

    @classmethod
    def cross_reference_switches(cls, attach_groups, switches, target, results):
        # target is either vrf or network
        for attach_group in attach_groups:
            for switch in attach_group.get("switches"):
                if switch.get("hostname"):
                    if not any(s.get("name") == switch.get("hostname") for s in switches):
                        if not any(s.get('management').get('management_ipv4_address') == switch.get("hostname") for s in switches):
                            if not any(s.get('management').get('management_ipv6_address') == switch.get("hostname") for s in switches):
                                ag = attach_group.get("name")
                                hn = switch.get("hostname")
                                results.append("{0} attach group {1} hostname {2} does not match any switch in the topology".format(target, ag, hn))

        return results

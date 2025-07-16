class Rule:
    id = "401"
    description = "Cross Reference VRFs and Networks items in the Service Model"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []

        switches = None
        sm_networks = None
        sm_vrfs = None
        network_attach_groups = None
        vrf_attach_groups = None

        switch_keys = ['vxlan', 'topology', 'switches']

        # Remove the check for overlay_services after deprecation
        # Remove lines 21 - 23
        overlay_key = 'overlay'
        check = cls.data_model_key_check(inventory, ['vxlan', overlay_key])
        if overlay_key in check['keys_not_found'] or overlay_key in check['keys_no_data']:
            overlay_key = 'overlay_services'

        check = cls.data_model_key_check(inventory, ['vxlan', overlay_key])
        if overlay_key in check['keys_found'] and overlay_key in check['keys_data']:
            network_keys = ['vxlan', overlay_key, 'networks']
            vrf_keys = ['vxlan', overlay_key, 'vrfs']
            network_attach_keys = ['vxlan', overlay_key, 'network_attach_groups']
            vrf_attach_keys = ['vxlan', overlay_key, 'vrf_attach_groups']

            # Check if vrfs, network and switch data is defined in the service model
            check = cls.data_model_key_check(inventory, switch_keys)
            if 'switches' in check['keys_data']:
                switches = cls.safeget(inventory, switch_keys)
            if not switches:
                # No switches defined in the service model, no reason to continue
                return results

            check = cls.data_model_key_check(inventory, network_keys)
            if 'networks' in check['keys_data']:
                sm_networks = cls.safeget(inventory, network_keys)

            check = cls.data_model_key_check(inventory, vrf_keys)
            if 'vrfs' in check['keys_data']:
                sm_vrfs = cls.safeget(inventory, vrf_keys)

            check = cls.data_model_key_check(inventory, vrf_attach_keys)
            if 'vrf_attach_groups' in check['keys_data']:
                vrf_attach_groups = cls.safeget(inventory, vrf_attach_keys)

            check = cls.data_model_key_check(inventory, network_attach_keys)
            if 'network_attach_groups' in check['keys_data']:
                network_attach_groups = cls.safeget(inventory, network_attach_keys)

            # Ensure Network is not referencing a VRF that is not defined in the service model
            results = cls.cross_reference_vrfs_nets(sm_vrfs, sm_networks, results)

            if sm_vrfs and vrf_attach_groups:
                results = cls.cross_reference_switches(vrf_attach_groups, switches, 'vrf', results)
            if sm_networks and network_attach_groups:
                results = cls.cross_reference_switches(network_attach_groups, switches, 'network', results)

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
    def safeget(cls, dict, keys):
        # Utility function to safely get nested dictionary values
        for key in keys:
            if dict is None:
                return None
            if key in dict:
                dict = dict[key]
            else:
                return None

        return dict

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
                        f"Network ({net.get('name')}) is referencing VRF ({net.get('vrf_name')}) "
                        "which is not defined in the service model. Add the VRF to the service model or remove the network from the service model "
                        "and re-run the playbook."
                    )

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
                                results.append(f"{target} attach group {ag} hostname {hn} does not match any switch in the topology.")

        return results

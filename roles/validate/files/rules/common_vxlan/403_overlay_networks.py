class Rule:
    id = "403"
    description = "Verify Network attributes are enabled in fabric overlay services"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        fabric_netflow_status = False
        fabric_trm_status = False
        networks = []

        # Map fabric types to the keys used in the data model based on controller fabric types
        fabric_type_map = {
            "VXLAN_EVPN": "ibgp",
            "eBGP_VXLAN": "ebgp",
        }

        fabric_type = fabric_type_map.get(data_model['vxlan']['fabric']['type'])

        netflow_keys = ['vxlan', 'global', fabric_type]
        check = cls.data_model_key_check(data_model, netflow_keys)
        if fabric_type in check['keys_found']:
            netflow_keys = ['vxlan', 'global', fabric_type, 'netflow', 'enable']
            check = cls.data_model_key_check(data_model, netflow_keys)

        if fabric_type in check['keys_not_found'] or 'enable' in check['keys_not_found']:
            netflow_keys = ['vxlan', 'global', 'netflow', 'enable']
            check = cls.data_model_key_check(data_model, netflow_keys)

        if 'enable' in check['keys_found']:
            fabric_netflow_status = cls.safeget(data_model, netflow_keys)
            if fabric_netflow_status is None:
                fabric_netflow_status = False

        underlay_trm_keys = ['vxlan', 'underlay', 'multicast', 'ipv4', 'trm_enable']
        check = cls.data_model_key_check(data_model, underlay_trm_keys)
        if 'trm_enable' in check['keys_found']:
            # Cannot use safeget yet without updating code check below as it looks for False vs None
            # fabric_trm_status = cls.safeget(data_model, trm_keys)
            fabric_trm_status = data_model["vxlan"]["underlay"]["multicast"]["ipv4"].get("trm_enable", False)

        network_keys = ['vxlan', 'overlay', 'networks']
        check = cls.data_model_key_check(data_model, network_keys)
        if 'networks' in check['keys_data']:
            networks = data_model["vxlan"]["overlay"]["networks"]
        else:
            network_keys = ['vxlan', 'overlay_services', 'networks']
            check = cls.data_model_key_check(data_model, network_keys)
            if 'networks' in check['keys_data']:
                networks = data_model["vxlan"]["overlay_services"]["networks"]

        # if data_model.get("vxlan", None):
        #     if data_model["vxlan"].get("overlay", None) or data_model["vxlan"].get("overlay_services", None):
        #         if data_model["vxlan"].get("overlay").get("networks", None):
        #             networks = data_model["vxlan"]["overlay"]["networks"]
        #         elif data_model["vxlan"].get("overlay_services").get("networks", None):
        #             networks = data_model["vxlan"]["overlay_services"]["networks"]

        # Map each network_attach_group name to the set of switch hostnames it contains.
        # Used to detect a switch attached through more than one group on the same network.
        group_switches = {}
        network_attach_groups = cls.safeget(data_model, ['vxlan', 'overlay', 'network_attach_groups'])
        if not network_attach_groups:
            network_attach_groups = cls.safeget(data_model, ['vxlan', 'overlay_services', 'network_attach_groups'])
        for grp in network_attach_groups or []:
            group_switches[grp.get('name')] = {
                sw.get('hostname') for sw in grp.get('switches', []) if sw.get('hostname')
            }

        for network in networks:
            if "network_attach_group" in network and "network_attach_groups" in network:
                results.append(
                    f"vxlan.overlay.networks.{network['name']} cannot define both 'network_attach_group' "
                    "and 'network_attach_groups'. Only one of these attributes can be used."
                )

            results = cls.check_duplicate_attach_switches(
                network, group_switches, 'vxlan.overlay.networks', results
            )

            current_network_netflow_status = network.get("netflow_enable", None)
            if current_network_netflow_status is not None:
                if fabric_netflow_status is False and current_network_netflow_status is True:
                    results.append(
                        f"For vxlan.overlay.networks.{network['name']}.netflow_enable to be enabled, "
                        f"first vxlan.global.netflow.enable must be enabled (true)."
                    )
                    break

            if fabric_netflow_status and current_network_netflow_status:
                current_network_netflow_monitor = network.get("vlan_netflow_monitor", None)
                if current_network_netflow_monitor is None:
                    results.append(
                        f"When vxlan.overlay.networks.{network['name']}.netflow_enable is enabled, "
                        f"then vxlan.overlay.networks.{network['name']}.vlan_netflow_monitor must be set "
                        "to a valid value from vxlan.global.netflow."
                    )
                    break

            current_network_trm_status = network.get("trm_enable", None)
            if current_network_trm_status is not None:
                if fabric_trm_status is False and current_network_trm_status is True:
                    results.append(
                        f"For vxlan.overlay.networks.{network['name']}.trm_enable to be enabled, "
                        f"first vxlan.underlay.multicast.ipv4.trm_enable must be enabled (true)."
                    )
                    break

        return results

    @classmethod
    def check_duplicate_attach_switches(cls, network, group_switches, dm_path, results):
        # A switch attached through more than one of a network's network_attach_groups
        # would render duplicate attachment entries, so flag it as invalid.
        group_names = network.get('network_attach_groups')
        if not group_names:
            return results

        hostname_groups = {}
        for grp_name in group_names:
            for hostname in group_switches.get(grp_name, set()):
                hostname_groups.setdefault(hostname, set()).add(grp_name)

        for hostname, grps in hostname_groups.items():
            if len(grps) > 1:
                results.append(
                    f"{dm_path}.{network['name']} attaches switch '{hostname}' through multiple "
                    f"network_attach_groups ({', '.join(sorted(grps))}). A switch can only be "
                    "attached through one group per network."
                )

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

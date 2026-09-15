class Rule:
    id = "204"
    description = "Verify Network attributes are set for multisite overlay vs standalone fabric overlay"
    severity = "HIGH"

    msg = "Network {0} attribute '{1}' must be defined under vxlan.multisite.overlay.networks under the 'child_fabrics:' key."

    @classmethod
    def match(cls, data_model):
        results = []
        child_fabric_attributes = [
            'dhcp_loopback_id',
            'dhcp_servers',
            'multicast_group_address',
            'trm_enable',
            'netflow_enable',
            'vlan_netflow_monitor',
            'l3gw_on_border'
        ]

        network_keys = ['vxlan', 'multisite', 'overlay', 'networks']
        check = cls.data_model_key_check(data_model, network_keys)
        if 'networks' in check['keys_found'] and 'networks' in check['keys_data']:
            networks = data_model['vxlan']['multisite']['overlay']['networks']

            # Map each network_attach_group name to the set of switch hostnames it contains.
            # Used to detect a switch attached through more than one group on the same network.
            group_switches = {}
            network_attach_groups = cls.safeget(
                data_model, ['vxlan', 'multisite', 'overlay', 'network_attach_groups']
            )
            for grp in network_attach_groups or []:
                group_switches[grp.get('name')] = {
                    sw.get('hostname') for sw in grp.get('switches', []) if sw.get('hostname')
                }

            for network in networks:
                if "network_attach_group" in network and "network_attach_groups" in network:
                    results.append(
                        f"vxlan.multisite.overlay.networks.{network['name']} cannot define both 'network_attach_group' "
                        "and 'network_attach_groups'. Only one of these attributes can be used."
                    )

                results = cls.check_duplicate_attach_switches(
                    network, group_switches, 'vxlan.multisite.overlay.networks', results
                )

                for attr in network:
                    if attr in child_fabric_attributes:
                        results.append(cls.msg.format(network['name'], attr))

                for child_fabric in network.get('child_fabrics', []):
                    if not child_fabric.get('netflow_enable') and child_fabric.get('vlan_netflow_monitor'):
                        results.append(
                            f"Network {network['name']} attribute 'netflow_monitor' can only be defined "
                            "if 'vlan_netflow_monitor' is true under the 'child_fabrics:' key."
                        )

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

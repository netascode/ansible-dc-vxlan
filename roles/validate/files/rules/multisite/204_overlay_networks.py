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
            for network in networks:
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

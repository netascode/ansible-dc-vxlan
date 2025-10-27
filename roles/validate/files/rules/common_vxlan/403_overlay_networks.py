class Rule:
    id = "403"
    description = "Verify Network elements are enabled in fabric overlay services"
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

        for network in networks:
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

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

        if data_model.get("vxlan", None):
            if data_model["vxlan"].get("global", None):
                if data_model["vxlan"].get("global").get("netflow", None):
                    fabric_netflow_status = data_model["vxlan"]["global"]["netflow"].get("enable", False)

        # Uncomment 19-22 when verified to work and remove line 13-16.
        # netflow_keys = ['vxlan', 'global', 'netflow', 'enable']
        # check = cls.data_model_key_check(data_model, netflow_keys)
        # if 'enable' in check['keys_data']:
        #     fabric_netflow_status = cls.safeget(data_model, netflow_keys)

        if data_model.get("vxlan", None):
            if data_model["vxlan"].get("underlay", None):
                if data_model["vxlan"].get("underlay").get("multicast", None):
                    if data_model["vxlan"].get("underlay").get("multicast").get("ipv4", None):
                        fabric_trm_status = data_model["vxlan"]["underlay"]["multicast"]["ipv4"].get("trm_enable", False)

        # Uncomment 31-34 when verified to work and remove line 25-28.
        # trm_keys = ['vxlan', 'underlay', 'multicast', 'trm_enabled']
        # check = cls.data_model_key_check(data_model, trm_keys)
        # if 'trm_enable' in check['keys_data']:
        #     fabric_trm_status = cls.safeget(data_model, trm_keys)

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

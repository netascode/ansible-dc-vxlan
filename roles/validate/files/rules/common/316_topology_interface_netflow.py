class Rule:
    id = "316"
    description = "Verify interface enable_netflow is only used when fabric-level netflow is enabled"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        fabric_netflow_status = False

        fabric_type_map = {
            "VXLAN_EVPN": "ibgp",
            "eBGP_VXLAN": "ebgp",
        }

        fabric_type_check = cls.data_model_key_check(
            data_model, ['vxlan', 'fabric', 'type']
        )
        if 'type' not in fabric_type_check['keys_found']:
            return results
        fabric_type = fabric_type_map.get(
            data_model['vxlan']['fabric']['type']
        )

        netflow_keys = ['vxlan', 'global', fabric_type, 'netflow', 'enable']
        check = cls.data_model_key_check(data_model, netflow_keys)

        if 'enable' not in check['keys_found']:
            netflow_keys = ['vxlan', 'global', 'netflow', 'enable']
            check = cls.data_model_key_check(data_model, netflow_keys)

        if 'enable' in check['keys_found']:
            fabric_netflow_status = cls.safeget(data_model, netflow_keys)
            if fabric_netflow_status is None:
                fabric_netflow_status = False

        switches_check = cls.data_model_key_check(
            data_model, ['vxlan', 'topology', 'switches']
        )
        if 'switches' not in switches_check['keys_data']:
            return results

        switches = data_model['vxlan']['topology']['switches']

        for switch in switches:
            for interface in switch.get('interfaces', []):
                current_iface_netflow = interface.get('enable_netflow', None)
                if current_iface_netflow is True and fabric_netflow_status is False:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"enable_netflow to be enabled, "
                        f"first vxlan.global.{fabric_type}.netflow.enable "
                        f"(or vxlan.global.netflow.enable) must be enabled (true)."
                    )

        return results

    @classmethod
    def data_model_key_check(cls, tested_object, keys):
        dm_key_dict = {
            'keys_found': [], 'keys_not_found': [],
            'keys_data': [], 'keys_no_data': [],
        }
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
        for key in keys:
            if dict is None:
                return None
            if key in dict:
                dict = dict[key]
            else:
                return None
        return dict

class Rule:
    id = "314"
    description = (
        "Verify that enable_qos_stats is only set on interfaces where QoS is "
        "enabled. NDFC's DISABLE_QOS_STATS field is only meaningful when "
        "ENABLE_QOS=true; setting enable_qos_stats without enable_qos: true "
        "will silently produce no configuration."
    )
    severity = "MEDIUM"

    @classmethod
    def match(cls, data_model):
        results = []
        switches = []

        check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' in check['keys_data']:
            switches = data_model.get('vxlan').get('topology').get('switches')
        else:
            return results

        # Pre-merge check: only report when the user explicitly sets enable_qos_stats
        # on an interface AND has not explicitly set enable_qos: true on the same
        # interface. If the user relies on merged defaults for enable_qos, this rule
        # will still fire — the user should set enable_qos: true explicitly on the
        # interface where enable_qos_stats matters.
        for switch in switches:
            for interface in switch.get('interfaces', []) or []:
                if 'enable_qos_stats' not in interface:
                    continue
                if interface.get('enable_qos') is not True:
                    results.append(
                        f"vxlan.topology.switches.{switch.get('name')}."
                        f"interfaces.{interface.get('name')}.enable_qos_stats: "
                        f"is set but enable_qos is not true; the DISABLE_QOS_STATS "
                        "field will not be emitted to NDFC. Set enable_qos: true "
                        "on the interface, or remove enable_qos_stats."
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

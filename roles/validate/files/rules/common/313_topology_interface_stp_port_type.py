class Rule:
    id = "313"
    description = (
        "Verify that spanning_tree_port_type is not set to a non-'none' value "
        "while spanning_tree_portfast is enabled on the same interface "
        "(NDFC template constraint: PORTTYPE_FAST_ENABLED=true is incompatible "
        "with SPANNING_TREE_PORT_TYPE != 'no')"
    )
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        switches = []

        check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' in check['keys_data']:
            switches = data_model.get('vxlan').get('topology').get('switches')
        else:
            return results

        # Pre-merge data: user-set spanning_tree_portfast defaults to True in every
        # interface profile, so we cannot reliably distinguish "user did not set it"
        # from "user set it to true". The invariant is enforced unconditionally
        # whenever spanning_tree_port_type is set to a value other than 'none' —
        # if the effective portfast is false the user must set spanning_tree_portfast
        # explicitly to false on the interface for this rule to pass.
        for switch in switches:
            for interface in switch.get('interfaces', []) or []:
                port_type = interface.get('spanning_tree_port_type')
                if port_type is None or port_type == 'none':
                    continue
                portfast = interface.get('spanning_tree_portfast')
                # Only allow port_type != 'none' when user explicitly disables portfast
                if portfast is not False:
                    results.append(
                        f"vxlan.topology.switches.{switch.get('name')}."
                        f"interfaces.{interface.get('name')}.spanning_tree_port_type: "
                        f"cannot be '{port_type}' when spanning_tree_portfast is enabled; "
                        "set spanning_tree_portfast: false on the interface, "
                        "or use spanning_tree_port_type: 'none'"
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

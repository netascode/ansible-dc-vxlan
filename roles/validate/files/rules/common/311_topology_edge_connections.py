class Rule:
    id = "311"
    description = "Verify edge connections have valid source devices and interfaces"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        edge_connections = []
        switches = []

        # Check if edge_connections exists in the data model
        check_edge = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'edge_connections'])
        if 'edge_connections' in check_edge['keys_data']:
            edge_connections = data_model.get("vxlan").get("topology").get("edge_connections")
        else:
            return results

        # Check if switches exists in the data model
        check_switches = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' in check_switches['keys_data']:
            switches = data_model.get("vxlan").get("topology").get("switches")
        else:
            return results

        # Build a list of valid switch names
        valid_switch_names = [switch.get("name") for switch in switches if switch.get("name")]

        for edge_connection in edge_connections:
            source_device = edge_connection.get("source_device", "")
            source_interface = edge_connection.get("source_interface", "")

            # Verify source_device exists in topology.switches
            if source_device and source_device not in valid_switch_names:
                results.append(
                    f"vxlan.topology.edge_connections.{source_device} source_device does not exist in topology.switches."
                )

            # Verify source_interface does not contain a '.'
            if source_interface and '.' in source_interface:
                results.append(
                    f"vxlan.topology.edge_connections.{source_device}.{source_interface} source_interface must not contain a '.' (sub-interfaces are not allowed)."
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

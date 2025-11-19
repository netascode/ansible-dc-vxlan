import re


class Rule:
    id = "305"
    description = "Verify vPC interfaces are compliant with vPC configuration requirements"
    severity = "HIGH"

    # Check if vPC interfaces are compliant with vPC configuration requirements
    @classmethod
    def match(cls, data_model):
        # initialize results list, vpc_interfaces_dict and vpc_interfaces_dict_parameters dictionaries, vpc_params_to_match list and vpc_peers_list
        results = []
        vpc_interfaces_dict = {}
        vpc_interfaces_dict_parameters = {}
        vpc_params_to_match = [
            "mtu",
            "speed",
            "enabled",
            "spanning_tree_portfast",
            "pc_mode",
        ]
        vpc_peers_list = cls.get_vpc_peers(data_model)
        # Check if fabric topology switches are defined
        switches = []
        if data_model.get("vxlan", None):
            if data_model["vxlan"].get("topology", None):
                if data_model.get("vxlan").get("topology").get("switches", None):
                    switches = data_model.get("vxlan").get("topology").get("switches")
        for switch in switches:
            switch_name = switch["name"]
            # Check if interfaces are defined
            if switch.get("interfaces"):
                vpc_ids = []
                # Iterate through interfaces
                for interface in switch.get("interfaces"):
                    # Normalize interface name
                    interface_name = cls.normalize_interface_name(interface.get("name"))
                    # Check if vPC id is defined
                    if interface.get("vpc_id"):
                        vpc_id = interface.get("vpc_id")

                        # Check if switch is part of a vPC peer group
                        is_peer = False
                        for pairs in vpc_peers_list:
                            if switch_name in pairs:
                                is_peer = True
                                break
                        if not is_peer:
                            results.append(
                                f"Switch {switch_name} is not part of a vPC peer group but "
                                f"has vPC id {vpc_id} defined on interface {interface_name}."
                            )
                            return results

                        # Enforce Port-channel ID matches vPC ID to avoid mismatched configurations
                        port_channel_match = re.fullmatch(
                            r"Port-channel(\d+)", interface_name
                        )
                        if port_channel_match:
                            port_channel_id = port_channel_match.group(1)
           
                            if int(port_channel_id) != int(vpc_id):
                                results.append(
                                    f"Switch {switch_name} interface {interface_name} uses vPC id {vpc_id} but Port-channel ID {port_channel_id}; these values must match."
                                )

                        # Check if vPC id is referenced by more than 1 Port-channel on the switch
                        if vpc_id in vpc_ids:
                            results.append(
                                f"vpc_id : {vpc_id} is referenced by more than 1 Port-channel on switch {switch_name}"
                            )
                        else:
                            vpc_ids.append(vpc_id)
                        # create vpc_interfaces_dict in below format
                        #   {
                        #   "45": {
                        #     "dc2-leaf2": "Port-channel33",
                        #     "dc2-leaf1": "Port-channel33"
                        #   },
                        #   "46": {
                        #     "dc2-leaf2": "Port-channel34"
                        #   },
                        #   "47": {
                        #     "dc2-leaf2": "Port-channel35",
                        #     "dc2-leaf1": "Port-channel35",
                        #     "dc2-leaf3": "Port-channel35"
                        #   }
                        # }
                        vpc_interfaces_dict[vpc_id] = vpc_interfaces_dict.get(
                            vpc_id, {}
                        )
                        vpc_interfaces_dict[vpc_id][switch_name] = vpc_interfaces_dict[
                            vpc_id
                        ].get(switch_name, "")
                        vpc_interfaces_dict[vpc_id][switch_name] = interface_name
                        # create vpc_interfaces_dict_parameters in below format
                        # {
                        #   "45": {
                        #     "interfaces": {
                        #       "dc2-leaf2:Port-channel33": {
                        #         "mtu": "default",
                        #         "speed": "auto",
                        #         "enabled": false,
                        #         "spanning_tree_portfast": true,
                        #         "pc_mode": "active"
                        #       },
                        #       "dc2-leaf1:Port-channel33": {
                        #         "mtu": "jumbo",
                        #         "speed": null,
                        #         "enabled": true,
                        #         "spanning_tree_portfast": true,
                        #         "pc_mode": "active"
                        #       }
                        #     }
                        #   },
                        #   "46": {
                        #     "interfaces": {
                        #       "dc2-leaf2:Port-channel34": {
                        #         "mtu": "default",
                        #         "speed": "auto",
                        #         "enabled": false,
                        #         "spanning_tree_portfast": true,
                        #         "pc_mode": "active"
                        #       }
                        #     }
                        #   }
                        # }
                        vpc_interfaces_dict_parameters[
                            vpc_id
                        ] = vpc_interfaces_dict_parameters.get(vpc_id, {})
                        vpc_id_int = switch_name + ":" + interface_name
                        vpc_interfaces_dict_parameters[vpc_id][
                            "interfaces"
                        ] = vpc_interfaces_dict_parameters[vpc_id].get("interfaces", {})
                        vpc_interfaces_dict_parameters[vpc_id]["interfaces"][
                            vpc_id_int
                        ] = vpc_interfaces_dict_parameters[vpc_id]["interfaces"].get(
                            vpc_id_int, {}
                        )
                        for param in vpc_params_to_match:
                            vpc_interfaces_dict_parameters[vpc_id]["interfaces"][
                                vpc_id_int
                            ][param] = interface.get(param)

        for vpc_id, switch_interfaces in vpc_interfaces_dict.items():
            # Check if vPC id is referenced by more than 2 switches
            for pairs in vpc_peers_list:
                switch_interfaces_pair = {}
                for pair in pairs:
                    if pair in switch_interfaces:
                        switch_interfaces_pair.update({pair: switch_interfaces[pair]})

                # Check if vPC id is only referenced by a single switch but must be referenced by both vPC peer switches
                if len(switch_interfaces_pair) > 0 and len(switch_interfaces_pair) < 2:
                    results.append(
                        f"vpc_id : {vpc_id} is only referenced by a single switch {', '.join(switch_interfaces_pair.keys())} "
                        "but must be referenced by both vPC peer switches"
                    )

        for vpc_id, interfaces in vpc_interfaces_dict_parameters.items():
            # Check if vPC interfaces have same values for parameters on vpc_params_to_match list
            if len(interfaces["interfaces"]) == 2:
                for param in vpc_params_to_match:
                    if (
                        interfaces["interfaces"][
                            list(interfaces["interfaces"].keys())[0]
                        ][param]
                        != interfaces["interfaces"][
                            list(interfaces["interfaces"].keys())[1]
                        ][param]
                    ):
                        results.append(
                            f"vpc_id : {vpc_id} interfaces {', '.join(interfaces['interfaces'].keys())} have different {param} values"
                        )
        return results

    # Normalize interface name
    @classmethod
    def normalize_interface_name(cls, interface_name):
        # Replace 'eth' or 'e' followed by digits with 'Ethernet' followed by the same digits
        interface_name = re.sub(
            r"(?i)^(?:e|eth(?:ernet)?)(\d(?:\/\d+){1,2})$",
            r"Ethernet\1",
            interface_name,
            flags=re.IGNORECASE,
        )

        # Replace 'Po' followed by digits with 'Port-channel' followed by the same digits
        interface_name = re.sub(
            r"(?i)^(po|port-channel)([1-9]|[1-9][0-9]{1,3}|[1-3][0-9]{3}|40([0-8][0-9]|9[0-6]))$",
            r"Port-channel\2",
            interface_name,
            flags=re.IGNORECASE,
        )

        # Replace 'eth' or 'e' followed by digits with 'Ethernet' followed by the same digits (for sub interface)
        interface_name = re.sub(
            r"(?i)^(?:e|eth(?:ernet)?)(\d(?:\/\d+){1,2}\.\d{1,4})$",
            r"Ethernet\1",
            interface_name,
            flags=re.IGNORECASE,
        )

        # Replace 'Lo' or 'Loopback' followed by digits with 'Loopback' followed by the same digits
        interface_name = re.sub(
            r"(?i)^(lo|loopback)([0-9]|[1-9][0-9]{1,2}|10[0-1][0-9]|102[0-3])$",
            r"Loopback\2",
            interface_name,
            flags=re.IGNORECASE,
        )

        return interface_name

    # Get vpc pairs from fabric topology vpc_peers
    @classmethod
    def get_vpc_peers(cls, data_model):
        vpc_peers_list = []
        if data_model.get("vxlan", None):
            if data_model["vxlan"].get("topology", None):
                if data_model.get("vxlan").get("topology").get("vpc_peers", None):
                    for vpc_peers in (
                        data_model.get("vxlan").get("topology").get("vpc_peers")
                    ):
                        vpc_peers_list.append(
                            sorted([vpc_peers.get("peer1"), vpc_peers.get("peer2")])
                        )
        return vpc_peers_list

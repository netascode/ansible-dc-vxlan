class Rule:
    id: str = "208"
    description: str = "Verify IP address when manual_underlay_allocation is true"
    severity: str = "HIGH"

    results = []

    @classmethod
    def match(cls, inventory):

        # Check if required keys exist in the inventory
        check = cls.data_model_key_check(inventory, ['vxlan', 'underlay', 'general', 'manual_underlay_allocation'])
        if 'manual_underlay_allocation' not in check['keys_data']:
            # If manual_underlay_allocation key is missing, no need to proceed
            return cls.results
        # Check if manual_underlay_allocation is set to true
        general = cls.safeget(inventory, ['vxlan', 'underlay', 'general'])
        if general.get("enable_ipv6_underlay"):
            underlay_af = 6
        else:
            underlay_af = 4
        if "manual_underlay_allocation" in general and underlay_af == 4:
            # Check if anycast_rp is configured:
            # Check if anycast_rp is configured
            check = cls.data_model_key_check(inventory, ['vxlan', 'underlay', 'multicast', 'ipv4'])
            if 'ipv4' not in check['keys_data']:
                cls.results.append("vxlan.underlay.multicast.ipv4.anycast_rp must be configured when manual_underlay_allocation is true.")
                return cls.results

            multicast_ipv4 = cls.safeget(inventory, ['vxlan', 'underlay', 'multicast', 'ipv4'])
            if "anycast_rp" not in multicast_ipv4:
                cls.results.append("vxlan.underlay.multicast.ipv4.anycast_rp must be configured when manual_underlay_allocation is true.")

        # Extract the underlay routing loopback IDs
        underlay_general = cls.safeget(inventory, ["vxlan", "underlay", "general"])
        underlay_routing_loopback_id = underlay_general.get("underlay_routing_loopback_id")
        underlay_vtep_loopback_id = underlay_general.get("underlay_vtep_loopback_id")

        # Verify IDs are defined
        if underlay_routing_loopback_id is None or underlay_vtep_loopback_id is None:
            return cls.results.append("Missing underlay_routing_loopback_id or underlay_vtep_loopback_id in vxlan.underlay.general.")

        # Check if required keys exist in the inventory
        check = cls.data_model_key_check(inventory, ['vxlan', 'topology', 'switches'])
        if 'switches' not in check['keys_data']:
            # If switches key is missing, no need to proceed
            return cls.results

        # Extract the list of switches
        switches = cls.safeget(inventory, ["vxlan", "topology", "switches"])
        for switch in switches:
            switch_name = switch.get("name")

            if "interfaces" not in switch:
                cls.results.append(f"Missing interfaces in vxlan.topology.switches.{switch_name}")
                return cls.results
            interfaces = switch.get("interfaces")

            routing_loopback_name = f"loopback{underlay_routing_loopback_id}"
            vtep_loopback_name = f"loopback{underlay_vtep_loopback_id}"

            if underlay_af == 4:
                routing_loopback_found = cls.check_interface_with_ipv4(interfaces, routing_loopback_name)
                vtep_loopback_found = cls.check_interface_with_ipv4(interfaces, vtep_loopback_name)
                if not routing_loopback_found:
                    cls.results.append(
                        f"Switch '{switch_name}' is missing a configured interface '{routing_loopback_name}' with an IPv{underlay_af} address."
                    )
                if not vtep_loopback_found:
                    cls.results.append(
                        f"Switch '{switch_name}' is missing a configured interface '{vtep_loopback_name}' with an IPv{underlay_af} address."
                    )

            if underlay_af == 6:
                routing_loopback_found = cls.check_interface_with_ipv6(interfaces, routing_loopback_name)
                vtep_loopback_found = cls.check_interface_with_ipv6(interfaces, vtep_loopback_name)
                if not routing_loopback_found:
                    cls.results.append(
                        f"Switch '{switch_name}' is missing a configured interface '{routing_loopback_name}' with an IPv{underlay_af} address."
                    )
                if not vtep_loopback_found:
                    cls.results.append(
                        f"Switch '{switch_name}' is missing a configured interface '{vtep_loopback_name}' with an IPv{underlay_af} address."
                    )
                if switch.get('manual_ipv6_router_id', None) is None:
                    cls.results.append(
                        f"Switch '{switch_name}' is missing a configured switches.manual_ipv6_router_id' with an IPv{underlay_af} address."
                    )

        check = cls.data_model_key_check(inventory, ["vxlan", "topology", "fabric_links"])
        interface_numbering_v4 = cls.safeget(inventory, ["vxlan", "underlay", "ipv4"])
        interface_numbering_v6 = cls.safeget(inventory, ["vxlan", "underlay", "ipv6"])
        if (
            'fabric_links' not in check['keys_data']
            and (
                (interface_numbering_v4 and interface_numbering_v4.get("fabric_interface_numbering") == "p2p")
                or (interface_numbering_v6 and interface_numbering_v6.get("enable_ipv6_link_local_address") is False)
            )
        ):
            cls.results.append(
                "Fabric Links is not configured, but P2P subnet is expected in this configuration."
            )

        # Check if vtep_ip exist in vpc_peers
        cls.validate_vpc_peers_and_vtep_vip(inventory)

        return cls.results

    @classmethod
    def validate_vpc_peers_and_vtep_vip(cls, inventory):
        """
        Validates vPC peers and ensures vtep_vip is defined and unique when manual_underlay_allocation is true.
        """
        check = cls.data_model_key_check(inventory, ["vxlan", "topology", "vpc_peers"])
        if 'vpc_peers' not in check['keys_data']:
            # If switches key is missing, no need to proceed
            return cls.results
        vpc_peers = cls.safeget(inventory, ["vxlan", "topology", "vpc_peers"])
        vtep_vip_list = set()
        vpc_peers_list = []

        for peer in vpc_peers:
            peer_name = f"{peer.get('peer1')}-{peer.get('peer2')}"
            vpc_peers_list.append(peer_name)
            vtep_vip = peer.get("vtep_vip", False)
            # Check if vtep_vip is defined
            if not vtep_vip:
                cls.results.append(f"vPC peer '{peer_name}' is missing a defined vtep_vip address.")
                continue

            # Check if vtep_vip is unique
            if vtep_vip in vtep_vip_list:
                cls.results.append(f"Duplicate vtep_vip address '{vtep_vip}' found for vPC peer '{peer_name}'.")
            else:
                vtep_vip_list.add(vtep_vip)

            check = cls.data_model_key_check(inventory, ["vxlan", "underlay", "ipv4"])
            if 'ipv4' in check['keys_data']:
                interface_numbering = cls.safeget(inventory, ["vxlan", "underlay", "ipv4"])

                # Check IP address under vxlan.topology.fabric_link only if
                # fabric numbering is P2P or fabric peering is false (Use Fabric Peer-Link)
                if peer.get("fabric_peering") is False or interface_numbering["fabric_interface_numbering"] == "p2p":
                    cls.validate_fabric_links(inventory, vpc_peers_list)

            check = cls.data_model_key_check(inventory, ["vxlan", "underlay", "ipv6"])
            if 'ipv6' in check['keys_data']:
                interface_numbering = cls.safeget(inventory, ["vxlan", "underlay", "ipv6"])
                # Check IP address under vxlan.topology.fabric_link only if
                # fabric numbering is global or fabric peering is false (Use Fabric Peer-Link)
                if peer.get("fabric_peering") is False or interface_numbering["enable_ipv6_link_local_address"] is False:
                    cls.validate_fabric_links(inventory, vpc_peers_list)

    @classmethod
    def validate_fabric_links(cls, inventory, vpc_peers_list):
        """
        Validates fabric links to ensure that IP configuration is present for vPC peer connections.
        """
        interface_numbering_v4 = cls.safeget(inventory, ["vxlan", "underlay", "ipv4"])
        interface_numbering_v6 = cls.safeget(inventory, ["vxlan", "underlay", "ipv6"])

        check = cls.data_model_key_check(inventory, ["vxlan", "topology", "fabric_links"])

        if 'fabric_links' not in check['keys_data']:
            if vpc_peers_list:
                cls.results.append("vxlan.topology.fabric_links not found but vpc_peers is not empty.")
                return cls.results
            else:
                # If switches key is missing, no need to proceed
                return cls.results

        fabric_links = cls.safeget(inventory, ["vxlan", "topology", "fabric_links"])
        fabric_links_list = []

        for link in fabric_links:
            source_device = link.get("source_device")
            dest_device = link.get("dest_device")
            fabric_links_name = f"{source_device}-{dest_device}"
            fabric_links_list.append(fabric_links_name)
            ipv4_config = link.get("ipv4", {})
            ipv6_config = link.get("ipv6", {})
            # Check IPv4 configuration
            if interface_numbering_v4:
                if len(ipv4_config.keys()) > 0 and (not ipv4_config.get("subnet") or not ipv4_config.get("source_ipv4") or not ipv4_config.get("dest_ipv4")):
                    cls.results.append(
                        f"Fabric link between '{source_device}' and '{dest_device}' is missing a valid IPv4 configuration."
                    )
                if len(ipv4_config.keys()) == 0 and interface_numbering_v4.get("fabric_interface_numbering", None) == "p2p":
                    cls.results.append(
                        f"Fabric link between '{source_device}' and '{dest_device}' is missing a valid IPv4 configuration."
                    )
            # Check IPv6 configuration
            if interface_numbering_v6:
                if len(ipv6_config.keys()) > 0 and (not ipv6_config.get("subnet") or not ipv6_config.get("source_ipv6") or not ipv6_config.get("dest_ipv6")):
                    cls.results.append(
                        f"Fabric link between '{source_device}' and '{dest_device}' is missing a valid IPv6 configuration."
                    )
                if len(ipv6_config.keys()) == 0 and interface_numbering_v6["enable_ipv6_link_local_address"] is False:
                    cls.results.append(
                        f"Fabric link between '{source_device}' and '{dest_device}' is missing a valid IPv6 configuration."
                    )
        # Check if vpc_peers is on fabric_link
        vpc_peers = cls.safeget(inventory, ["vxlan", "topology", "vpc_peers"])
        for peer in vpc_peers:
            peer1 = f"{peer.get('peer1')}-{peer.get('peer2')}"
            peer2 = f"{peer.get('peer2')}-{peer.get('peer1')}"
            if not (peer1 in fabric_links_list or peer2 in fabric_links_list):
                cls.results.append(
                    f"Fabric link between '{peer1}' and '{peer2}' is missing."
                )

    @classmethod
    def check_interface_with_ipv4(cls, interfaces, loopback_name):
        """
        Helper method to check if a specific loopback interface exists and has an IPv4 address.
        """
        # Create a short_name to catch both values allowed in the schema and change to lower to compare them
        short_name = loopback_name.replace("loopback", "lo")
        for interface in interfaces:
            intf = interface.get("name").lower()
            if (intf == loopback_name.lower() or intf == short_name.lower()) and interface.get("ipv4_address"):
                return True
        return False

    @classmethod
    def check_interface_with_ipv6(cls, interfaces, loopback_name):
        """
        Helper method to check if a specific loopback interface exists and has an IPv6 address.
        """
        # Create a short_name to catch both values allowed in the schema and change to lower to compare them
        short_name = loopback_name.replace("loopback", "lo")
        for interface in interfaces:
            intf = interface.get("name").lower()
            if (intf == loopback_name.lower() or intf == short_name.lower()) and interface.get("ipv6_address"):
                return True
        return False

    @classmethod
    def data_model_key_check(cls, tested_object, keys):
        """
        Checks if specific keys exist in a nested object and whether they have data.
        """
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
        """
        Utility function to safely get nested dictionary values
        """
        for key in keys:
            if dict is None:
                return None
            if key in dict:
                dict = dict[key]
            else:
                return None

        return dict

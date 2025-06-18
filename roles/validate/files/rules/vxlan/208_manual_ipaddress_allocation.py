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
        manual_allocation = inventory.get("vxlan").get("underlay").get("general").get("manual_underlay_allocation")
        if manual_allocation:
            # Check if anycast_rp is configured
            anycast_rp = inventory.get("vxlan").get("underlay").get("multicast").get("ipv4").get("anycast_rp")
            if not anycast_rp:
                cls.results.append("vxlan.underlay.multicast.ipv4.anycast_rp must be configured when manual_underlay_allocation is true.")

        # Extract the underlay routing loopback IDs
        underlay_general = inventory.get("vxlan").get("underlay").get("general")
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
        switches = inventory.get("vxlan").get("topology").get("switches")
        for switch in switches:
            switch_name = switch.get("name")
            interfaces = switch.get("interfaces")

            # Check for Loopback{underlay_routing_loopback_id}
            routing_loopback_name = f"loopback{underlay_routing_loopback_id}"
            routing_loopback_found = cls.check_interface_with_ipv4(interfaces, routing_loopback_name)

            if not routing_loopback_found:
                cls.results.append(
                    f"Switch '{switch_name}' is missing a configured interface '{routing_loopback_name}' with an IPv4 address."
                )

            # Check for Loopback{underlay_vtep_loopback_id}
            vtep_loopback_name = f"loopback{underlay_vtep_loopback_id}"
            vtep_loopback_found = cls.check_interface_with_ipv4(interfaces, vtep_loopback_name)

            if not vtep_loopback_found:
                cls.results.append(
                    f"Switch '{switch_name}' is missing a configured interface '{vtep_loopback_name}' with an IPv4 address."
                )

        # Check if vtep_ip exist in vpc_peers
        cls.validate_vpc_peers_and_vtep_vip(inventory)

        return cls.results

    @classmethod
    def validate_vpc_peers_and_vtep_vip(cls, inventory):
        """
        Validates VPC peers and ensures vtep_vip is defined and unique when manual_underlay_allocation is true.
        """
        results = []

        check = cls.data_model_key_check(inventory, ["vxlan", "topology", "vpc_peers"])
        if 'vpc_peers' not in check['keys_data']:
            # If switches key is missing, no need to proceed
            return cls.results
        vpc_peers = inventory.get("vxlan").get("topology").get("vpc_peers")
        vtep_vip_list = set()
        vpc_peers_list = []

        for peer in vpc_peers:
            peer_name = f"{peer.get('peer1')}-{peer.get('peer2')}"
            vpc_peers_list.append(peer_name)
            vtep_vip = peer.get("vtep_vip", False)
            # Check if vtep_vip is defined
            if not vtep_vip :
                cls.results.append(f"VPC peer '{peer_name}' is missing a defined vtep_vip address.")
                continue

            # Check if vtep_vip is unique
            if vtep_vip in vtep_vip_list:
                cls.results.append(f"Duplicate vtep_vip address '{vtep_vip}' found for VPC peer '{peer_name}'.")
            else:
                vtep_vip_list.add(vtep_vip)
        cls.validate_fabric_links(inventory, vpc_peers_list)

    @classmethod
    def validate_fabric_links(cls, inventory, vpc_peers_list):
        """
        Validates fabric links to ensure that IPv4 configuration is present for VPC peer connections.
        """
        check = cls.data_model_key_check(inventory, ["vxlan", "topology" , "fabric_links"])

        if 'fabric_links' not in check['keys_data']:
            if vpc_peers_list:
                cls.results.append("vxlan.topology.fabric_links not found but vpc_peers is not empty.")
                return cls.results
            else:
                # If switches key is missing, no need to proceed
                return cls.results

        fabric_links = inventory.get("vxlan").get("topology").get("fabric_links")
        fabric_links_list = []

        for link in fabric_links:
            source_device = link.get("source_device")
            dest_device = link.get("dest_device")
            fabric_links_name = f"{source_device}-{dest_device}"
            fabric_links_list.append(fabric_links_name)
            ipv4_config = link.get("ipv4", {})

            # Check IPv4 configuration
            if not ipv4_config or not ipv4_config.get("subnet") or not ipv4_config.get("source_ipv4") or not ipv4_config.get("dest_ipv4"):
                cls.results.append(
                    f"Fabric link between '{source_device}' and '{dest_device}' is missing a valid IPv4 configuration."
                )

            # Check if vpc_peers is on fabric_link
        vpc_peers = inventory.get("vxlan").get("topology").get("vpc_peers")
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
            if interface.get("name").lower() == loopback_name.lower() or interface.get("name").lower() == short_name.lower() and interface.get("ipv4_address"):
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

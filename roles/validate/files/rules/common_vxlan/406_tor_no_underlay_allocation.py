class Rule:
    id = "406"
    description = "Verify TOR switches do not have VXLAN underlay configuration when manual_underlay_allocation is true"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []

        check = cls.data_model_key_check(data_model, ['vxlan', 'underlay', 'general', 'manual_underlay_allocation'])
        if 'manual_underlay_allocation' not in check['keys_data']:
            return results

        general = cls.safeget(data_model, ['vxlan', 'underlay', 'general'])
        if not general.get("manual_underlay_allocation"):
            return results

        check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' not in check['keys_data']:
            return results

        switches = cls.safeget(data_model, ["vxlan", "topology", "switches"])
        tor_names = {sw.get("name", "") for sw in switches if sw.get("role", "").lower() == "tor"}

        if not tor_names:
            return results

        underlay_general = cls.safeget(data_model, ["vxlan", "underlay", "general"])
        routing_lo_id = underlay_general.get("underlay_routing_loopback_id")
        vtep_lo_id = underlay_general.get("underlay_vtep_loopback_id")

        for switch in switches:
            switch_name = switch.get("name")
            switch_role = switch.get("role", "").lower()

            if switch_role != "tor":
                continue

            interfaces = switch.get("interfaces", [])
            for interface in interfaces:
                intf_name = interface.get("name", "").lower()
                if intf_name in (f"loopback{routing_lo_id}", f"lo{routing_lo_id}",
                                 f"loopback{vtep_lo_id}", f"lo{vtep_lo_id}"):
                    if interface.get("ipv4_address"):
                        results.append(
                            f"TOR switch '{switch_name}': underlay loopback '{interface.get('name')}' with IPv4 "
                            "should not be defined (TOR switches do not participate in VXLAN underlay)."
                        )

        # Check TOR vPC peers vtep_vip
        check = cls.data_model_key_check(data_model, ["vxlan", "topology", "vpc_peers"])
        if 'vpc_peers' in check['keys_data']:
            vpc_peers = cls.safeget(data_model, ["vxlan", "topology", "vpc_peers"])
            switch_role_map = {sw.get("name", ""): sw.get("role", "").lower() for sw in switches}

            for peer in vpc_peers:
                peer1_role = switch_role_map.get(peer.get("peer1", ""), "")
                peer2_role = switch_role_map.get(peer.get("peer2", ""), "")
                if peer1_role == "tor" or peer2_role == "tor":
                    if peer.get("vtep_vip"):
                        peer_name = f"{peer.get('peer1')}-{peer.get('peer2')}"
                        results.append(
                            f"vPC peer '{peer_name}': vtep_vip should not be defined for TOR switches "
                            "(TOR switches do not participate in VXLAN underlay)."
                        )

        # Check TOR fabric links have no IPv4
        check = cls.data_model_key_check(data_model, ["vxlan", "topology", "fabric_links"])
        if 'fabric_links' in check['keys_data']:
            fabric_links = cls.safeget(data_model, ["vxlan", "topology", "fabric_links"])
            for link in fabric_links:
                src = link.get("source_device", "")
                dst = link.get("dest_device", "")
                ipv4_config = link.get("ipv4", {})

                if not ipv4_config:
                    continue

                if src in tor_names or dst in tor_names:
                    tor_device = src if src in tor_names else dst
                    if ipv4_config.get("subnet") or ipv4_config.get("source_ipv4") or ipv4_config.get("dest_ipv4"):
                        results.append(
                            f"Fabric link '{src}' → '{dst}': IPv4 underlay configuration should not be defined "
                            f"for TOR switch '{tor_device}' (TOR switches do not participate in VXLAN underlay)."
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
        for key in keys:
            if dict is None:
                return None
            if key in dict:
                dict = dict[key]
            else:
                return None
        return dict

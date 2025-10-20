"""
Validation Rules scenarios:
1.  Switches in the vxlan.overlay_extensions.vrf_lites.switches should be defined in the vxlan.topology.switches
2.  BGP and OSPF should be defined in two different policy.
    vxlan.overlay_extensions.vrf_lites.ospf
    vxlan.overlay_extensions.vrf_lites.bgp
    vxlan.overlay_extensions.vrf_lites.switches.bgp
    vxlan.overlay_extensions.vrf_lites.switches.bgp_peers
    vxlan.overlay_extensions.vrf_lites.switches.interfaces.ospf
3.  route_reflector_client for AF IPv4 and IPv6 config should not be allowed.
    vxlan.overlay_extensions.vrf_lites.switches.bgp_peers.address_family_ipv4_unicast.route_reflector_client
    vxlan.overlay_extensions.vrf_lites.switches.bgp_peers.address_family_ipv6_unicast.route_reflector_client
4.  Check if OSPF Authentication is enabled, key must be provided
    vxlan.overlay_extensions.vrf_lites.switches.interfaces.ospf.auth_key
5.  Check AREA 0 is standard
    vxlan.overlay_extensions.vrf_lites.ospf.areas.area_type
6.  Check static routes across Policies
    vxlan.overlay_extensions.vrf_lites.switches.static_routes
7.  Check ospf network type for Loopback
    vxlan.overlay_extensions.vrf_lites.switches.interfaces.ospf.network_type
"""

OSPF_VERSIONS = ["ospf", "ospfv3"]

class Rule:
    """
    Class 502 - Verify VRF-Lites Cross Reference Between Policies, Groups, and Switches
    """

    id = "502"
    description = "Verify VRF-Lites Cross Reference Between Policies, Groups, and Switches"
    severity = "HIGH"
    results = []

    @classmethod
    def match(cls, data_model):
        """
        function used by iac-validate
        """
        vrf_lites = []
        topology_switches = []
        policies = []
        switch_policy = []
        static_routes_compliance = []

        if data_model.get("vxlan", {}).get("fabric", {}).get("type") == "eBGP_VXLAN":
            cls.results.append("VRF-Lite is not supported for eBGP_VXLAN yet.")
            return cls.results

        # Get fabric switches
        if data_model.get("vxlan", {}).get("topology", {}).get("switches") is not None:
            topology_switches = data_model["vxlan"]["topology"]["switches"]

        # Get vrf-lites policies
        if data_model.get("vxlan", {}).get("overlay_extensions", {}).get("vrf_lites") is not None:
            vrf_lites = data_model["vxlan"]["overlay_extensions"]["vrf_lites"]

        # Check Global Level
        for policy in vrf_lites:
            if policy.get("name", None):
                policies.append(policy["name"])
                cls.check_global_ospf_process(policy)
                cls.check_global_ospf_and_bgp(policy)
                cls.check_global_ospf_area(policy)
                # Check switch Level and update static_routes_compliance if exists
                if policy.get("switches"):
                    # Backward compatibility with bgp_asn at the global level
                    fabric_type = None
                    fabric_type_map = {
                        "VXLAN_EVPN": "ibgp",
                        "External": "external"
                    }
                    fabric_type = fabric_type_map.get(data_model["vxlan"]["fabric"].get("type"))
                    bgp_asn = cls.safeget(data_model, ["vxlan", "global", fabric_type, "bgp_asn"]) if fabric_type else None
                    if bgp_asn is None:
                        bgp_asn = cls.safeget(data_model, ["vxlan", "global", "bgp_asn"])
                    for switch_policy in policy["switches"]:
                        cls.check_switch_level(
                            switch_policy,
                            policy,
                            bgp_asn,
                            topology_switches,
                            static_routes_compliance,
                        )
        cls.check_route_compliance_across_policies(static_routes_compliance)

        return cls.results

    @classmethod
    def check_global_ospf_and_bgp(cls, policy):
        """
        Check if OSPF, OSPFv3 or BGP are enabled in the global policy
        """
        for ospf_version in OSPF_VERSIONS:
            if {ospf_version, "bgp"}.issubset(policy):
                cls.results.append(
                    f"vxlan.overlay_extensions.vrf_lites.{policy['name']}.{ospf_version}, "
                    f"vxlan.overlay_extensions.vrf_lites.{policy['name']}.bgp. "
                    f"BGP and {ospf_version.upper()} are defined in the same vrf-lite entry; "
                    "please use two different vrf-lite entries."
                )

        if {"ospf", "ospfv3"}.issubset(policy):
            cls.results.append(
                f"vxlan.overlay_extensions.vrf_lites.{policy['name']}.ospf, "
                f"vxlan.overlay_extensions.vrf_lites.{policy['name']}.ospfv3. "
                "OSPF and OSPFv3 are defined in the same vrf-lite entry; "
                "please use two different vrf-lite entries."
            )

    @classmethod
    def check_global_ospf_process(cls, policy):
        """
        Check OSPF Process
        """
        for ospf_version in OSPF_VERSIONS:
            if policy.get(ospf_version) and not policy[ospf_version].get("process"):
                cls.results.append(
                    f"vxlan.overlay_extensions.vrf_lites.{policy['name']}.{ospf_version}.process. "
                    f"{ospf_version.upper()} process is not defined."
                )

    @classmethod
    def check_global_ospf_area(cls, policy):
        """
        Check OSPF if backbone area is standard
        """
        for ospf_version in OSPF_VERSIONS:
            if policy.get(ospf_version) and policy[ospf_version].get("areas"):
                for area in policy[ospf_version]["areas"]:
                    if "id" in area and area.get("area_type"):
                        # Check if AREA 0 is not standard
                        if area["id"] in (0, "0.0.0.0") and area["area_type"] != "standard":
                            cls.results.append(
                                f"vxlan.overlay_extensions.vrf_lites.{policy['name']}.{ospf_version}.areas.id.0. "
                                f"area_type is defined to {area['area_type']}. "
                                "Backbone area is always standard"
                            )
                        elif area["area_type"] == "nssa":
                            cls.check_global_ospf_nssa(area, policy["name"])

    @classmethod
    def check_global_ospf_nssa(cls, area, policy):
        """
        Check NSSA parameters
        """
        if "nssa" in area:
            if "translate" in area["nssa"]:
                translate = area["nssa"]["translate"]
                if "never" in translate and translate["never"] is True:
                    if ("supress_fa" in translate or "always" in translate) and (
                        translate["supress_fa"] is True or translate["always"] is True
                    ):
                        cls.results.append(
                            f"vxlan.overlay_extensions.vrf_lites.{policy}.ospf.areas.id.{area['id']}. "
                            f"NSSA translate type 7 never, cannot be enabled with always or supress"
                        )
            if "route_map" in area["nssa"] and (
                "default_information_originate" not in area["nssa"]
                or area["nssa"]["default_information_originate"] is False
            ):
                cls.results.append(
                    f"vxlan.overlay_extensions.vrf_lites.{policy}.ospf.areas.id.{area['id']}. "
                    f"route-map couldn't be used without default_information_originate"
                )

    @classmethod
    def check_switch_level(
        cls,
        switch_policy,
        policy,
        infra_bgp_asn,
        topology_switches,
        static_routes_compliance,
    ):
        """
        Check switch level
        """
        ospf = False
        ospfv3 = False
        bgp = False

        # Check (bgp or bgp_peer) at the switch level
        if "bgp" in switch_policy or "bgp_peers" in switch_policy:
            bgp = True
            if "bgp_peers" in switch_policy:
                cls.check_switch_bgp_route_reflector(
                    switch=switch_policy["name"],
                    bgp_peers=switch_policy["bgp_peers"],
                    fabric_asn=infra_bgp_asn,
                    policy=policy["name"],
                )

        # Check OSPF at the switch level
        if switch_policy.get("interfaces", None):
            for interface in switch_policy["interfaces"]:
                if interface.get("ospf"):
                    ospf = True
                    cls.check_switch_ospf(
                        interface["ospf"],
                        switch_policy["name"],
                        interface["name"],
                        policy["name"],
                    )

        # Check OSPFv3 at the switch level
        if switch_policy.get("interfaces", None):
            for interface in switch_policy["interfaces"]:
                if interface.get("ospfv3"):
                    ospfv3 = True
                    cls.check_switch_ospf(
                        interface["ospfv3"],
                        switch_policy["name"],
                        interface["name"],
                        policy["name"],
                    )

        # Check if OSPF, OSPFv3 or BGP is enabled
        if (ospf or ospfv3) and bgp:
            ospf_ver_str = ""
            ospf_ver_str = "OSPF" if ospf else ""
            ospf_ver_str += ", " if ospf and ospfv3 else ""
            ospf_ver_str += "OSPFv3" if ospfv3 else ""

            cls.results.append(
                f"vxlan.overlay_extensions.vrf_lites.{policy['name']}.switches.{switch_policy['name']}. "
                f"BGP, {ospf_ver_str} are configured in the same policy at the switch level. "
                "Please use two different policies.-xx"
            )
        if ospf and ospfv3:
            cls.results.append(
                f"vxlan.overlay_extensions.vrf_lites.{policy['name']}.switches.{switch_policy['name']}. "
                "OSPF and OSPFv3 are configured in the same policy at the switch level. "
                "Please use two different policies."
            )

        # Check if switch exists in topology
        cls.check_switch_in_topology(
            switch_policy["name"], topology_switches, policy["name"]
        )

        # Check Static routes
        if "static_routes" in switch_policy:
            static_routes_compliance.append(
                {
                    "policy": policy["name"],
                    "vrf": policy["vrf"],
                    "switch": switch_policy["name"],
                    "prefix": switch_policy["static_routes"],
                })

    @classmethod
    def check_switch_in_topology(cls, switch, topology_switches, policy):
        """
        Check if switch is in the topology
        """
        if list(filter(lambda topo: topo["name"] == switch, topology_switches)):
            pass
        else:
            cls.results.append(
                f"vxlan.overlay_extensions.vrf_lites.{policy}.switches.{switch} "
                "is not defined in vxlan.topology.switches"
            )

    @classmethod
    def check_switch_ospf(cls, ospf, switch, interface=None, policy=None):
        """
        Check OSPF parameters
        """
        # Check if key exists if authentication is enabled
        if "auth_type" in ospf and ospf["auth_type"] is not None:
            if "auth_key" not in ospf:
                cls.results.append(
                    f"In the policy: {policy}, auth_type is {ospf['auth_type']} "
                    "but auth_key is missing"
                )

        # Check if Network type for Loopback interface is not Broadcast
        if ospf.get("network_type"):
            if (interface.startswith("Lo") or interface.startswith("lo")) and ospf[
                "network_type"
            ] == "broadcast":
                cls.results.append(
                    f"vxlan.overlay_extensions.vrf_lites.{policy}.switches.{switch}.interfaces.{interface}.ospf. "
                    f"network_type: {ospf['network_type']}"
                    " is not supported with Loopback"
                )

        # Check if Adversise-subnet is used only for Loopback in ospf
        if ospf.get("advertise_subnet"):
            if (
                not (interface.startswith("Lo") or interface.startswith("lo"))
                and ospf["advertise_subnet"]
            ):
                cls.results.append(
                    f"vxlan.overlay_extensions.vrf_lites.{policy}.switches.{switch}.interfaces.{interface}.ospf. "
                    f"advertise_subnet: True is only supported with Loopback"
                )

        # Check if passive-interface is used only for Loopback in ospf
        if ospf.get("passive_interface"):
            if (interface.startswith("Lo") or interface.startswith("lo")) and ospf[
                "passive_interface"
            ]:
                cls.results.append(
                    f"vxlan.overlay_extensions.vrf_lites.{policy}.switches.{switch}.interfaces.{interface}.ospf. "
                    f"passive_interface: True is not supported with Loopback"
                )

    @classmethod
    def check_switch_bgp_route_reflector(cls, switch, bgp_peers, fabric_asn, policy):
        """
        Check if route-reflector is enabled in eBGP
        """
        for bgp_peer in bgp_peers:
            # Check RR for AF IPv4
            if bgp_peer.get("address_family_ipv4_unicast"):
                if bgp_peer["address_family_ipv4_unicast"].get(
                    "route_reflector_client"
                ):
                    if (
                        bgp_peer["address_family_ipv4_unicast"][
                            "route_reflector_client"
                        ]
                        is True
                    ):
                        if bgp_peer["remote_as"] != fabric_asn:
                            cls.results.append(
                                f"vxlan.overlay_extensions.vrf_lites.{policy}.switches.{switch}.bgp_peers.{bgp_peer['address']}.address_family_ipv4_unicast"
                                f"route_reflector_client: {bgp_peer['address_family_ipv4_unicast']['route_reflector_client']} "
                                "is not allowed in eBGP"
                            )

            # Check RR for AF IPv6
            if bgp_peer.get("address_family_ipv6_unicast"):
                if bgp_peer["address_family_ipv6_unicast"].get(
                    "route_reflector_client"
                ):
                    if (
                        bgp_peer["address_family_ipv6_unicast"][
                            "route_reflector_client"
                        ]
                        is True
                    ):
                        if bgp_peer["remote_as"] != fabric_asn:
                            cls.results.append(
                                f"vxlan.overlay_extensions.vrf_lites.{policy}.switches.{switch}.bgp_peers.{bgp_peer['address']}.address_family_ipv6_unicast"
                                f"route_reflector_client: {bgp_peer['address_family_ipv6_unicast']['route_reflector_client']} "
                                "is not allowed in eBGP"
                            )

    @classmethod
    def check_route_compliance_across_policies(cls, routes):
        """
        Check routes compliance across policies
        """

        def sort_prefixes_and_next_hops(data_input):
            """
            Sort prefixes and next_hops
            """
            for item in data_input:
                # Sort static_ipv4 prefixes
                if 'static_ipv4' in item['prefix']:
                    for static_ipv4_entry in item['prefix']['static_ipv4']:
                        # Sort next_hops by 'ip'
                        if "next_hops" in static_ipv4_entry:
                            static_ipv4_entry['next_hops'] = sorted(
                                static_ipv4_entry['next_hops'],
                                key=lambda x: x['ip']
                            )
                        else:
                            cls.results.append(
                                f"vxlan.overlay_extensions.vrf_lites.{item['policy']}.switches.{item['switch']}"
                                f".static_routes.static_ipv4.{static_ipv4_entry} "
                                f"next_hops is not defined."
                            )

                    # Sort static_ipv4 by 'prefix'
                    item['prefix']['static_ipv4'] = sorted(
                        item['prefix']['static_ipv4'],
                        key=lambda x: x['prefix']
                    )
                # Sort static_ipv6 prefixes
                if 'static_ipv6' in item['prefix']:
                    for static_ipv6_entry in item['prefix']['static_ipv6']:
                        # Sort next_hops by 'ip'
                        if "next_hops" in static_ipv6_entry:
                            static_ipv6_entry['next_hops'] = sorted(
                                static_ipv6_entry['next_hops'],
                                key=lambda x: x['ip']
                            )
                        else:
                            cls.results.append(
                                f"vxlan.overlay_extensions.vrf_lites.{item['policy']}.switches.{item['switch']}"
                                f".static_routes.static_ipv6.{static_ipv6_entry} "
                                f"next_hops is not defined."
                            )

                    # Sort static_ipv6 by 'prefix'
                    item['prefix']['static_ipv6'] = sorted(
                        item['prefix']['static_ipv6'],
                        key=lambda x: x['prefix']
                    )

            return data_input

        sorted_data = sort_prefixes_and_next_hops(routes)

        for data in sorted_data:
            for data2 in sorted_data:
                if data['vrf'] == data2['vrf'] and data['switch'] == data2['switch']:
                    if data['prefix'] != data2['prefix']:
                        cls.results.append(
                            f"vxlan.overlay_extensions.vrf_lites.{data['policy']} and vxlan.overlay_extensions.vrf_lites.{data2['policy']} "
                            f"use the same VRF and switch with different static routes"
                        )

    @classmethod
    def safeget(cls, dictionary, keys):
        """
        Safely retrieves nested values from a dictionary using a list of keys.
        """
        for key in keys:
            if dictionary is None or key not in dictionary:
                return None
            dictionary = dictionary[key]
        return dictionary

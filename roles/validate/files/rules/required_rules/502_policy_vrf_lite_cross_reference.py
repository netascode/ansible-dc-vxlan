'''
Validation Rules scenarios:
1.  Switches in the [insert vrf-lite switch model key structure here] should be defined in the vxlan.topology.switches
2.  BGP and OSPF should be defined in two different policy.
3.  route_reflector_client for AF IPv4 and IPv6 config should not be allowed.
4.  Check if OSPF Authentication is enabled, key must be provided
5.  Check AREA 0 is standard
6.  Check static routes across Policies
7.  Check ospf network type for Loopback
'''


class Rule:
    id = "502"
    description = "Verify VRF-Lites Cross Reference Between Policies, Groups, and Switches"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        vrf_lites = []
        topology_switches = []
        policies = []
        results = []
        switch_policy = []
        static_routes_compliance = []

        # Get fabric switches
        if inventory.get("vxlan"):
            if inventory["vxlan"].get("topology"):
                if inventory.get("vxlan").get("topology").get("switches"):
                    topology_switches = inventory.get("vxlan").get("topology").get("switches")

        # Get vrf-lites policies
        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("overlay_extensions", None):
                if inventory["vxlan"].get("overlay_extensions").get("vrf_lites", None):
                    vrf_lites = inventory["vxlan"]["overlay_extensions"]["vrf_lites"]

        for policy in vrf_lites:   # Check Global Level
            if policy.get('name', None):
                policies.append(policy['name'])

                cls.check_global_ospf_and_bgp(results, policy)
                cls.check_global_ospf_area(results, policy)

                if policy.get('switches'):  # Check switch Level
                    for switch_policy in policy['switches']:
                        cls.check_switch_level(results, switch_policy, policy,
                                               inventory["vxlan"]['global']['bgp_asn'],
                                               topology_switches, static_routes_compliance)

        return results

    @classmethod
    def check_global_ospf_and_bgp(cls, results, policy):
        '''
        Check if OSPF and BGP is enabled in the global policy
        '''
        if "ospf" in policy and "bgp" in policy:
            results.append(
                f"In the policy: {policy['name']}, BGP and OSPF are configured " +
                "in the same policy at the Global level. " +
                "Please use two different policies")

    @classmethod
    def check_global_ospf_area(cls, results, policy):
        '''
        Check OSPF if backbone area is standard
        '''
        if policy.get('ospf'):  # Check OSPF parameters
            if policy['ospf'].get('areas'):
                for area in policy['ospf']['areas']:
                    if "id" in area and area.get('area_type'):
                        # Check if AREA 0 is not standard
                        if ((area['id'] == 0 or area['id'] == '0.0.0.0')
                                and area['area_type'] != 'standard'):
                            results.append(
                                f"In the policy: {policy['name']}, area backbone (0) " +
                                "is always standard not {area['area_type']}"
                            )

    @classmethod
    def check_switch_level(cls, results, switch_policy, policy,
                           infra_bgp_asn, topology_switches, static_routes_compliance):
        '''
        Check switch level
        '''
        ospf = False
        bgp = False

        # Check (bgp or bgp_peer) at the switch level
        if "bgp" in switch_policy or "bgp_peers" in switch_policy:
            bgp = True
            if "bgp_peers" in switch_policy:
                cls.check_switch_bgp_route_reflector(results,
                                                     bgp_peers=switch_policy['bgp_peers'],
                                                     fabric_asn=infra_bgp_asn,
                                                     policy=policy['name'])

        # Check OSPF at the switch level
        if switch_policy.get('interfaces', None):
            for interface in switch_policy['interfaces']:
                if interface.get('ospf'):
                    ospf = True
                    cls.check_switch_ospf(results,
                                          interface['ospf'],
                                          interface['name'],
                                          policy['name'])

        # Check if OSPF and BGP is enabled
        if ospf is True and bgp is True:
            results.append(
                f"In the policy: {policy['name']}, " +
                "BGP and OSPF are configured in the same policy at the switch level. " +
                "Please use two different policies")

        # Check if switch exists in topology
        cls.check_switch_in_topology(results,
                                     switch_policy['name'],
                                     topology_switches,
                                     policy['name'])

        # Check Static routes
        if "static_routes" in switch_policy:
            static_routes_compliance.append({"policy": policy['name'],
                                             "vrf": policy['vrf'],
                                             "switch": switch_policy['name'],
                                             "routes": switch_policy['static_routes']})

        cls.check_route_compliance_across_policies(results, static_routes_compliance)

    @classmethod
    def check_switch_in_topology(cls, results, switch, topology_switches, policy):
        '''
        Check if switch is in the topology
        '''
        if list(filter(lambda topo: topo['name'] == switch, topology_switches)):
            pass
        else:
            results.append(
                f"In the policy: {policy}, switch {switch} is not defined in the topology inventory"
            )

    @classmethod
    def check_switch_ospf(cls, results, ospf, interface=None, policy=None):
        '''
        Check OSPF parameters
        '''
        # Check if key exists if authentication is enabled
        if "auth_type" in ospf and ospf['auth_type'] is not None:
            if "auth_key" not in ospf:
                results.append(
                    f"In the policy: {policy}, auth_type is {ospf['auth_type']} " +
                    "but auth_key is missing"
                )

        # Check if Network type for Loopback interface is not Broadcast
        if ospf.get('network_type'):
            if interface.startswith('Lo') and ospf['network_type'] == "broadcast":
                results.append(
                    f"In the policy: {policy}, network_type: " +
                    "broadcast is not supported with Loopback"
                )

        # Check if Adversise-subnet is used only for Loopback in ospf
        if ospf.get('advertise_subnet'):
            if not interface.startswith('Lo') and ospf['advertise_subnet']:
                results.append(
                    f"In the policy: {policy} is configured on {interface}, " +
                    "advertise_subnet: True is only supported with Loopback"
                )

    @classmethod
    def check_switch_bgp_route_reflector(cls, results, bgp_peers, fabric_asn, policy):
        '''
        Check if route-reflector is enabled in eBGP
        '''
        for bgp_peer in bgp_peers:
            # Check RR for AF IPv4
            if bgp_peer.get('address_family_ipv4_unicast'):
                if bgp_peer['address_family_ipv4_unicast'].get('route_reflector_client'):
                    if bgp_peer['address_family_ipv4_unicast']['route_reflector_client'] is True:
                        if bgp_peer['remote_as'] != fabric_asn:
                            results.append(
                                f"In the policy: {policy}, " +
                                "BGP route-reflector is not allowed in AF IPv4."
                            )

            # Check RR for AF IPv6
            if bgp_peer.get('address_family_ipv6_unicast'):
                if bgp_peer['address_family_ipv6_unicast'].get('route_reflector_client'):
                    if bgp_peer['address_family_ipv6_unicast']['route_reflector_client'] is True:
                        if bgp_peer['remote_as'] != fabric_asn:
                            results.append(
                                f"In the policy: {policy}, " +
                                "BGP route-reflector is not allowed in AF IPv6."
                            )

    @classmethod
    def check_route_compliance_across_policies(cls, results, routes):
        '''
        Check routes compliance across policies
        '''
        for route in routes:
            for route2 in routes:
                if route['vrf'] == route2['vrf']:
                    if route['switch'] == route2['switch']:
                        for nb_pref in range(len(route['routes'])):
                            # Check if same number of prefixes
                            if len(route['routes']) == len(route2['routes']):
                                # Check if prefixes are equal
                                base_pref = route['routes'][nb_pref]['prefix']
                                list_pref = route2['routes']
                                if list(filter(lambda pref: pref['prefix'] == base_pref, list_pref)):
                                    # Check route TAG
                                    if route['routes'][nb_pref]['route_tag'] == route2['routes'][nb_pref]['route_tag']:
                                        for nb_nh in range(len(route['routes'][nb_pref]['next_hops'])):
                                            # Check if number of Next-Hops are equal
                                            if len(route['routes'][nb_pref]['next_hops']) == len(route2['routes'][nb_pref]['next_hops']):
                                                base_nh = route['routes'][nb_pref]['next_hops'][nb_nh]['ip']
                                                list_nh = route2['routes'][nb_pref]['next_hops']
                                                # Check if next-hop are is present in the list
                                                if list(filter(lambda nh: nh['ip'] == base_nh, list_nh)):
                                                    pass
                                                else:
                                                    results.append(
                                                        f"In the policy {route['policy']} Next Hop are different. "
                                                        f"Local: {route['routes'][nb_pref]['next_hops']} "
                                                        f"- Remote: {route2['routes'][nb_pref]['next_hops']}"
                                                    )
                                                    break
                                            else:
                                                results.append(
                                                    f"In the policy {route['policy']} Nb Next Hop are different. "
                                                    f"Local: {route['routes'][nb_pref]['next_hops']} "
                                                    f"- Remote: {route2['routes'][nb_pref]['next_hops']}"
                                                )
                                                break
                                    else:
                                        results.append(
                                            f"In the policy {route['policy']} Route Tag are different. "
                                            f"Local: {route['routes'][nb_pref]['route_tag']} "
                                            f"- Remote: {route2['routes'][nb_pref]['route_tag']}"
                                        )
                                        break
                                else:
                                    results.append(
                                        f"In the policy {route['policy']} Prefixes are different. "
                                        f"Local: {route['routes'][nb_pref]['prefix']} "
                                        f"- Remote: {route2['routes'][nb_pref]['prefix']}"
                                    )
                                    break
                            else:
                                results.append(
                                    f"In the policy {route['policy']} Nb prefixes are different. "
                                    f"Local: {route['routes']} - Remote: {route2['routes']}"
                                )

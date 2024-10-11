'''
Validation Rules scenarios:
1.	Switches in the VRF policies should be a subset of the switches in the switch topology.
2.	BGP and OSPF in the same VRF Lite policy are not supported.
3.	route_reflector_client AF IPv4 and IPv6 config for the BGP peers should not be allowed.
4.  Check if OSPF Authentication is enabled, key is provided
5.  Check AREA 0 is standard
6.  Check static routes between Policies
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

        for policy in vrf_lites: # Check Global Policy
            if policy.get('name', None):
                policies.append(policy['name'])
                # Check if OSPF and BGP is enabled in the global policy
                if "ospf" in policy and "bgp" in policy:
                    results.append(
                                f"In the policy: {policy['name']}, BGP and OSPF are configured " +
                                  "in the same policy at the Global level." +
                                  "Please use two different policies"
                            )
                    break
                if policy.get('ospf'): # Check OSPF parameters
                    if policy['ospf'].get('areas'):
                        for area in policy['ospf']['areas']:
                            if "id" in area and area.get('area_type'):

                                # Check if AREA 0 is not standard
                                if ((area['id'] == 0 or area['id'] == '0.0.0.0') and
                                    area['area_type'] != 'standard') :
                                    results.append(
                                        f"In the policy: {policy['name']}, area backbone (0) " +
                                        "is always standard not {area['area_type']}"
                                    )
                                    break

                # Check per switches
                if policy.get('switches'):
                    for switch_policy in policy['switches']:
                        ospf = False
                        bgp = False

                        # Check (bgp or bgp_peer) are enabled at the switch level
                        if  "bgp" in switch_policy or "bgp_peers" in switch_policy:
                            bgp = True
                            for bgp_peer in switch_policy['bgp_peers']:
                                # Check RR for af IPv4
                                if bgp_peer.get('address_family_ipv4_unicast'):
                                    if bgp_peer['address_family_ipv4_unicast'].get('route_reflector_client'):
                                        if bgp_peer['address_family_ipv4_unicast']['route_reflector_client'] is True:
                                            if bgp_peer['remote_as'] != inventory["vxlan"]['global']['bgp_asn']:
                                                results.append(
                                                    f"In the policy: {policy['name']}, BGP route-reflector is not allowed in AF IPv4."
                                                )
                                                break

                                # Check RR for af IPv6
                                if bgp_peer.get('address_family_ipv6_unicast'):
                                    if bgp_peer['address_family_ipv6_unicast'].get('route_reflector_client'):
                                        if bgp_peer['address_family_ipv6_unicast']['route_reflector_client'] is True:
                                            if bgp_peer['remote_as'] != inventory["vxlan"]['global']['bgp_asn']:
                                                results.append(
                                                    f"In the policy: {policy['name']}, BGP route-reflector is not allowed in AF IPv6."
                                                )
                                                break

                        # Check OSPF is enabled at the switch -> interface level
                        if switch_policy.get('interfaces', None):
                            for interface in switch_policy['interfaces']:
                                if interface.get('ospf'): # Check if OSPF is enabled
                                    ospf = True

                                    # Check if Authentification is required and Key is not provided.
                                    if "auth_type" in interface['ospf'] and interface['ospf']['auth_type'] is not None:
                                        if "auth_key" not in interface['ospf']:
                                            results.append(
                                            f"In the policy: {policy['name']}, auth_type is {interface['ospf']['auth_type']} but auth_key is missing"
                                            )
                                            break
                                    # Check if Network type for Loopback interface is not Broadcast
                                    if interface['ospf'].get('network_type'):
                                        if interface['name'].startswith('Lo') and interface['ospf']['network_type'] == "broadcast":
                                            results.append(
                                                f"In the policy: {policy['name']}, network_type: broadcast is not supported with Loopback"
                                            )

                                    # Check if Adversise-subnet is used only for Loopback in ospf
                                    if interface['ospf'].get('advertise_subnet'):
                                        if not interface['name'].startswith('Lo') and interface['ospf']['advertise_subnet']:
                                            results.append(
                                                f"In the policy: {policy['name']} is configured on {interface['name']}, " +
                                                "advertise_subnet: True is only supported with Loopback"
                                            )


                        if ospf is True and bgp is True:
                            results.append(
                                        f"In the policy: {policy['name']}, BGP and OSPF are configured in the same policy at the switch level." +
                                        "Please use two different policies"
                            )
                            break

                        # Check if switch is in the topology
                        if list(filter(lambda topo: topo['name'] == switch_policy['name'],
                                       topology_switches)):
                            pass
                        else:
                            results.append(
                                f"In the policy: {policy['name']}, switch {switch_policy['name']} is not defined in the topology inventory"
                            )
                            break

                        # Check Static routes
                        if "static_routes" in switch_policy:
                            static_routes_compliance.append({"policy": policy['name'],
                                                             "vrf": policy['vrf'],
                                                             "switch": switch_policy['name'],
                                                             "routes": switch_policy['static_routes']})

        for route in static_routes_compliance:
            for route2 in static_routes_compliance:
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
                                                if list(filter(lambda nh: nh['ip'] == base_nh , list_nh)):
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
        return results

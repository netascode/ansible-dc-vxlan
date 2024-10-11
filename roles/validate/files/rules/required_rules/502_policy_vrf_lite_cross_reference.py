'''
Validation Rules scenarios:
1.	Switches in the VRF policies should be a subset of the switches in the switch topology.
2.	BGP and OSPF in the same VRF Lite policy are not supported.
3.	route_reflector_client config for the BGP peers should not be allowed.
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

        for policy in vrf_lites:
            if policy.get('name', None):
                policies.append(policy['name'])
                # Check if OSPF and BGP is enabled in the global policy
                if policy.get('ospf', None) and policy.get('bgp', None):
                    results.append(
                                f"In the policy: {policy['name']}, BGP and OSPF are configured in the same policy. Please use two different policies"
                            )
                    break

                # Check per switches
                if policy.get('switches'):
                    for switch_policy in policy['switches']:
                        ospf = False
                        bgp = False

                        # Check (bgp or bgp_peer) are enabled at the switch level
                        if  switch_policy.get('bgp', None) or switch_policy.get('bgp_peers', None):  # BGP is enabled
                            bgp = True
                            for bgp_peer in switch_policy['bgp_peers']:
                                if bgp_peer.get('address_family_ipv4_unicast'):
                                    if bgp_peer['address_family_ipv4_unicast'].get('route_reflector_client'):
                                        if bgp_peer['address_family_ipv4_unicast']['route_reflector_client'] is True:
                                            if bgp_peer['remote_as'] != inventory["vxlan"]['global']['bgp_asn']:
                                                results.append(
                                                    f"In the policy: {policy['name']}, BGP route-reflector is not allowed."
                                                )
                                                break

                        # Check OSPF is enabled at the switch -> interface level
                        if switch_policy.get('interfaces', None):
                            for interface in switch_policy['interfaces']:
                                if interface.get('ospf'): # Check if OSPF is enabled
                                    ospf = True

                        if ospf is True and bgp is True:
                            results.append(
                                        f"In the policy: {policy['name']}, BGP and OSPF are configured in the same policy. Please use two different policies"
                            )
                            break

                        if list(filter(lambda topo: topo['name'] == switch_policy['name'], topology_switches)):
                            pass
                        else:
                            results.append(
                                f"In the policy: {policy['name']}, switch {switch_policy['name']} is not defined in the topology inventory"
                            )
                            break

        return results

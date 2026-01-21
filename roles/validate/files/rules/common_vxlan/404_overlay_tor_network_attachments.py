class Rule:
    """
    Validate TOR switches in network_attach_groups are properly paired.

    This rule ensures that any TOR switch referenced in overlay network attachments
    (network_attach_groups) is also defined in topology.tor_peers. This prevents
    the scenario where a user removes a TOR pairing but forgets to remove the
    network attachments, which would cause NDFC API failures with:
    "Switches [serial] have overlays. Please undeploy and try again"

    Validation sequence matters:
    - When ADDING a TOR: First add to tor_peers, then add to network_attach_groups
    - When REMOVING a TOR: First remove from network_attach_groups, then remove from tor_peers
    """
    id = "404"
    description = "Validate TOR switches in network_attach_groups have valid pairings in tor_peers"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        """
        Check that all TOR switches referenced in network_attach_groups
        are also defined in topology.tor_peers.

        Returns:
            list: List of validation error messages
        """
        results = []

        # Get topology data
        topology = cls.safeget(data_model, ['vxlan', 'topology'])
        if not topology:
            return results

        # Get switches and tor_peers
        switches = topology.get('switches', [])
        tor_peers = topology.get('tor_peers', [])

        # Build set of TOR switch names from topology.switches (role=tor)
        tor_switches_in_topology = set()
        for sw in switches:
            if sw.get('role') == 'tor':
                tor_switches_in_topology.add(sw.get('name'))

        # Build set of TOR switch names from tor_peers
        tors_in_pairings = set()
        for peer in tor_peers:
            tor1 = cls._extract_name(peer.get('tor1'))
            tor2 = cls._extract_name(peer.get('tor2'))
            if tor1:
                tors_in_pairings.add(tor1)
            if tor2:
                tors_in_pairings.add(tor2)

        # Get overlay data
        overlay = cls.safeget(data_model, ['vxlan', 'overlay'])
        if not overlay:
            # Try legacy key
            overlay = cls.safeget(data_model, ['vxlan', 'overlay_services'])
        if not overlay:
            return results

        network_attach_groups = overlay.get('network_attach_groups', [])
        networks = overlay.get('networks', [])

        if not network_attach_groups:
            return results

        # Build mapping of attach group name to networks using it
        group_to_networks = {}
        for network in networks:
            group_name = network.get('network_attach_group')
            if group_name:
                if group_name not in group_to_networks:
                    group_to_networks[group_name] = []
                group_to_networks[group_name].append(network.get('name', 'unknown'))

        # Check each network_attach_group for TOR references
        for group in network_attach_groups:
            group_name = group.get('name', 'unknown')
            switches_in_group = group.get('switches', [])
            networks_using_group = group_to_networks.get(group_name, [])

            for switch_entry in switches_in_group:
                switch_hostname = switch_entry.get('hostname', '')
                tors = switch_entry.get('tors', [])

                for tor in tors:
                    tor_hostname = tor.get('hostname', '')
                    if not tor_hostname:
                        continue

                    # Check 1: TOR must exist in topology.switches with role=tor
                    if tor_hostname not in tor_switches_in_topology:
                        results.append(
                            f"vxlan.overlay.network_attach_groups[{group_name}]: "
                            f"TOR switch '{tor_hostname}' (under parent '{switch_hostname}') "
                            f"is not defined in vxlan.topology.switches with role 'tor'"
                        )
                        continue

                    # Check 2: TOR must be in tor_peers
                    if tor_hostname not in tors_in_pairings:
                        network_list = ', '.join(networks_using_group) if networks_using_group else 'none'
                        results.append(
                            f"vxlan.overlay.network_attach_groups[{group_name}]: "
                            f"TOR switch '{tor_hostname}' has network attachments "
                            f"(networks: {network_list}) but is not defined in vxlan.topology.tor_peers. "
                            f"Either add the TOR to tor_peers or remove it from network_attach_groups."
                        )

        return results

    @classmethod
    def _extract_name(cls, value):
        """Extract switch name from dict or string."""
        if not value:
            return None
        return value.get('name') if isinstance(value, dict) else value

    @classmethod
    def safeget(cls, dict_obj, keys):
        """Utility function to safely get nested dictionary values."""
        for key in keys:
            if dict_obj is None:
                return None
            if key in dict_obj:
                dict_obj = dict_obj[key]
            else:
                return None
        return dict_obj

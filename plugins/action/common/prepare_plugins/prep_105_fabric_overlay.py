# Copyright (c) 2024 Cisco Systems, Inc. and its affiliates
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# SPDX-License-Identifier: MIT

class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def _restructure_flat_to_nested(self, switches_list, topology_switches, tor_peers):
        """Transform a flat switches list into the nested structure with TOR
        entries under their parent leaf switches.

        Each TOR is placed under ALL of its parent leaves that are present in the
        attach group. If a parent leaf is not explicitly listed in the attach group,
        a synthetic leaf entry is created automatically from topology data.

        Args:
            switches_list: List of switch dicts from network_attach_group
            topology_switches: List of switch dicts from vxlan.topology.switches
            tor_peers: List of tor_peers dicts from vxlan.topology.tor_peers

        Returns:
            Restructured switches list with TOR entries nested under parent leaves
        """
        # Build set of TOR hostnames from topology
        tor_hostnames = {
            sw['name'] for sw in topology_switches if sw.get("role") == "tor"
        }

        # Build TOR -> parent leaves mapping from tor_peers
        # Each TOR maps to a list of its parent leaf hostnames
        tor_to_parents = {}
        for peer in tor_peers:
            parent_leaves = []
            if peer.get("parent_leaf1"):
                parent_leaves.append(peer['parent_leaf1'])
            if peer.get("parent_leaf2"):
                parent_leaves.append(peer['parent_leaf2'])

            for key in ("tor1", "tor2"):
                tor_name = peer.get(key)
                if tor_name:
                    tor_to_parents[tor_name] = parent_leaves

        # Build topology hostname -> switch data mapping for creating synthetic entries
        topology_by_name = {sw['name']: sw for sw in topology_switches}

        # Separate leaf entries and TOR entries
        leaf_entries = []
        tor_entries = []

        for sw in switches_list:
            hostname = sw.get("hostname", "")
            if hostname in tor_hostnames:
                tor_entries.append(sw)
            else:
                leaf_entries.append(sw)

        # Initialize empty 'tors' list for each leaf entry
        for leaf in leaf_entries:
            if "tors" not in leaf:
                leaf['tors'] = []

        # Build hostname -> leaf entry mapping for quick lookup
        leaf_by_hostname = {leaf['hostname']: leaf for leaf in leaf_entries}

        # Collect all required parent leaf hostnames from TOR entries
        # and create synthetic leaf entries for any that are not in the attach group
        for tor_entry in tor_entries:
            tor_hostname = tor_entry['hostname']
            parent_leaves = tor_to_parents.get(tor_hostname, [])
            for parent_hostname in parent_leaves:
                if parent_hostname not in leaf_by_hostname:
                    # Create a synthetic leaf entry from topology data
                    synthetic_leaf = {'hostname': parent_hostname, 'tors': []}
                    leaf_entries.append(synthetic_leaf)
                    leaf_by_hostname[parent_hostname] = synthetic_leaf

        # Assign each TOR to ALL of its parent leaves present in this attach group
        for tor_entry in tor_entries:
            tor_hostname = tor_entry['hostname']
            parent_leaves = tor_to_parents.get(tor_hostname, [])
            valid_parents = [p for p in parent_leaves if p in leaf_by_hostname]

            if valid_parents:
                for parent_hostname in valid_parents:
                    leaf_by_hostname[parent_hostname]['tors'].append(tor_entry)
            else:
                # No parent leaf defined in tor_peers - keep TOR as top-level entry
                leaf_entries.append(tor_entry)

        return leaf_entries

    def prepare(self):
        data_model = self.kwargs['results']['model_extended']

        # We don't have switches for Multisite fabrics so need special handling
        if data_model['vxlan']['fabric']['type'] in ('MSD', 'MCFG'):
            switches = []
        else:
            switches = data_model['vxlan']['topology']['switches']

        tor_peers = data_model['vxlan'].get("topology", {}).get("tor_peers", [])

        if data_model['vxlan']['fabric']['type'] in ('VXLAN_EVPN', 'eBGP_VXLAN'):
            # Rebuild sm_data['vxlan']['overlay']['vrf_attach_groups'] into
            # a structure that is easier to use.
            vrf_grp_name_list = []
            data_model['vxlan']['overlay']['vrf_attach_groups_dict'] = {}
            for grp in data_model['vxlan']['overlay']['vrf_attach_groups']:
                data_model['vxlan']['overlay']['vrf_attach_groups_dict'][grp['name']] = []
                vrf_grp_name_list.append(grp['name'])
                for switch in grp['switches']:
                    data_model['vxlan']['overlay']['vrf_attach_groups_dict'][grp['name']].append(switch)
                # If the switch is in the switch list and a hostname is used, replace the hostname with the management IP
                for switch in data_model['vxlan']['overlay']['vrf_attach_groups_dict'][grp['name']]:
                    if any(sw['name'] == switch['hostname'] for sw in switches):
                        found_switch = next((item for item in switches if item["name"] == switch['hostname']))
                        if found_switch.get('management').get('management_ipv4_address'):
                            switch['mgmt_ip_address'] = found_switch['management']['management_ipv4_address']
                        elif found_switch.get('management').get('management_ipv6_address'):
                            switch['mgmt_ip_address'] = found_switch['management']['management_ipv6_address']

            # Remove vrf_attach_group from vrf if the group_name is not defined
            for vrf in data_model['vxlan']['overlay']['vrfs']:
                if 'vrf_attach_group' in vrf:
                    if vrf.get('vrf_attach_group') not in vrf_grp_name_list:
                        del vrf['vrf_attach_group']

            # Rebuild sm_data['vxlan']['overlay']['network_attach_groups'] into
            # a structure that is easier to use.
            net_grp_name_list = []
            data_model['vxlan']['overlay']['network_attach_groups_dict'] = {}
            for grp in data_model['vxlan']['overlay']['network_attach_groups']:
                data_model['vxlan']['overlay']['network_attach_groups_dict'][grp['name']] = []
                net_grp_name_list.append(grp['name'])

                # Restructure flat TOR entries under parent leaves
                grp['switches'] = self._restructure_flat_to_nested(
                    grp['switches'], switches, tor_peers
                )

                for switch in grp['switches']:
                    data_model['vxlan']['overlay']['network_attach_groups_dict'][grp['name']].append(switch)
                # If the switch is in the switch list and a hostname is used, replace the hostname with the management IP
                for switch in data_model['vxlan']['overlay']['network_attach_groups_dict'][grp['name']]:
                    if any(sw['name'] == switch['hostname'] for sw in switches):
                        found_switch = next((item for item in switches if item["name"] == switch['hostname']))
                        if found_switch.get('management').get('management_ipv4_address'):
                            switch['mgmt_ip_address'] = found_switch['management']['management_ipv4_address']
                        elif found_switch.get('management').get('management_ipv6_address'):
                            switch['mgmt_ip_address'] = found_switch['management']['management_ipv6_address']

                    # Process nested TOR entries and resolve their management IPs
                    if 'tors' in switch and switch['tors']:
                        for tor in switch['tors']:
                            tor_hostname = tor.get('hostname')
                            if tor_hostname and any(sw['name'] == tor_hostname for sw in switches):
                                found_tor = next((item for item in switches if item["name"] == tor_hostname))
                                if found_tor.get('management').get('management_ipv4_address'):
                                    tor['mgmt_ip_address'] = found_tor['management']['management_ipv4_address']
                                elif found_tor.get('management').get('management_ipv6_address'):
                                    tor['mgmt_ip_address'] = found_tor['management']['management_ipv6_address']

            # Remove network_attach_group from net if the group_name is not defined
            for net in data_model['vxlan']['overlay']['networks']:
                if 'network_attach_group' in net:
                    if net.get('network_attach_group') not in net_grp_name_list:
                        del net['network_attach_group']

        self.kwargs['results']['model_extended'] = data_model
        return self.kwargs['results']

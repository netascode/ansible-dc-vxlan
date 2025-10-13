# Copyright (c) 2025 Cisco Systems, Inc. and its affiliates
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to do so, subject to the following conditions:
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

import re


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = ['vxlan', 'topology', 'tor_peers']

    def _get_switch(self, name, expected_role, switches, errors):
        switch = switches.get(name)
        if not switch:
            errors.append(f"Switch '{name}' referenced in tor_peers is not defined in vxlan.topology.switches")
            return None
        role = switch.get('role')
        if role != expected_role:
            errors.append(
                f"Switch '{name}' referenced in tor_peers must have role '{expected_role}', current role is '{role}'"
            )
        if not switch.get('serial_number'):
            errors.append(f"Switch '{name}' must define serial_number for tor pairing support")
        return switch

    def _resolve_port_channel_id(self, member, switch, errors):
        port_channel_id = member.get('port_channel_id')
        interface = member.get('interface')
        interface_name = None
        if isinstance(interface, dict):
            interface_name = interface.get('name')
        elif isinstance(interface, str):
            interface_name = interface
        if port_channel_id is None and interface_name:
            match = re.search(r'(\d+)$', interface_name)
            if match:
                port_channel_id = int(match.group(1))
        if port_channel_id is None:
            errors.append(
                f"Port-channel identifier is required for switch '{member.get('name')}' in tor_peers. "
                "Provide port_channel_id or interface name in the data model."
            )
            return None
        return int(port_channel_id)

    def _resolve_vpc_domain(self, peer, key, name_a, name_b, topology):
        if peer.get(key) is not None:
            return peer.get(key)
        if not (name_a and name_b):
            return None
        vpc_peers = topology.get('vpc_peers') or []
        for candidate in vpc_peers:
            peers = {candidate.get('peer1'), candidate.get('peer2')}
            if {name_a, name_b} == peers:
                return candidate.get('domain_id')
        return None

    def prepare(self):
        results = self.kwargs['results']
        model_data = results['model_extended']
        topology = model_data.get('vxlan', {}).get('topology', {})
        tor_peers = topology.get('tor_peers')

        if not tor_peers:
            return results

        switches = {sw.get('name'): sw for sw in topology.get('switches', []) if sw.get('name')}
        processed_pairs = []
        errors = []
        pairing_ids = set()

        for peer in tor_peers:
            error_count_start = len(errors)
            parent_leaf1 = peer.get('parent_leaf1')
            tor1 = peer.get('tor1')
            if not parent_leaf1 or not tor1:
                errors.append("Each tor_peers entry requires parent_leaf1 and tor1 definitions")
                continue

            leaf1_name = parent_leaf1.get('name')
            tor1_name = tor1.get('name')
            leaf1_switch = self._get_switch(leaf1_name, 'leaf', switches, errors)
            tor1_switch = self._get_switch(tor1_name, 'tor', switches, errors)

            parent_leaf2 = peer.get('parent_leaf2')
            tor2 = peer.get('tor2')

            leaf2_name = parent_leaf2.get('name') if parent_leaf2 else None
            tor2_name = tor2.get('name') if tor2 else None

            leaf2_switch = None
            tor2_switch = None

            if parent_leaf2:
                leaf2_switch = self._get_switch(leaf2_name, 'leaf', switches, errors)
            if tor2:
                tor2_switch = self._get_switch(tor2_name, 'tor', switches, errors)

            tor_vpc_peer = peer.get('tor_vpc_peer', peer.get('vpc_peer', False))

            if tor_vpc_peer and not tor2:
                errors.append(
                    f"tor_peers entry pairing '{leaf1_name}' to '{tor1_name}' is marked as tor_vpc_peer but tor2 is not provided"
                )
            if tor2 and not tor_vpc_peer:
                errors.append(
                    f"tor_peers entry pairing '{leaf1_name}' to '{tor1_name}' defines tor2 but tor_vpc_peer is false"
                )

            leaf_vpc_domain = self._resolve_vpc_domain(peer, 'leaf_vpc_domain_id', leaf1_name, leaf2_name, topology)
            tor_vpc_domain = self._resolve_vpc_domain(peer, 'tor_vpc_domain_id', tor1_name, tor2_name, topology)

            leaf_is_vpc = bool(leaf2_switch and leaf_vpc_domain)
            tor_is_vpc = bool(tor_vpc_peer and tor2_switch and tor_vpc_domain)

            if parent_leaf2 and not leaf_is_vpc:
                errors.append(
                    f"tor_peers entry referencing leaves '{leaf1_name}' and '{leaf2_name}' requires a vPC domain ID."
                )
            if tor_vpc_peer and not tor_is_vpc:
                errors.append(
                    f"tor_peers entry referencing tors '{tor1_name}' and '{tor2_name}' requires a tor_vpc_domain_id."
                )

            scenario = 'leaf_standalone_tor_standalone'
            if leaf_is_vpc and tor_is_vpc:
                scenario = 'leaf_vpc_tor_vpc'
            elif leaf_is_vpc and not tor_is_vpc:
                scenario = 'leaf_vpc_tor_standalone'
            elif not leaf_is_vpc and tor_is_vpc:
                errors.append(
                    f"Unsupported ToR pairing scenario: tor vPC with standalone leafs for '{tor1_name}'."
                )

            pairing_id = peer.get('pairing_id') or f"{leaf1_name}-{tor1_name}"
            if pairing_id in pairing_ids:
                errors.append(f"Duplicate tor pairing identifier '{pairing_id}' detected")
            pairing_ids.add(pairing_id)

            if leaf1_switch:
                leaf1_po = self._resolve_port_channel_id(parent_leaf1, leaf1_switch, errors)
                leaf1_serial = leaf1_switch.get('serial_number') if leaf1_switch else None
            else:
                leaf1_po = None
                leaf1_serial = None

            if tor1_switch:
                tor1_po = self._resolve_port_channel_id(tor1, tor1_switch, errors)
                tor1_serial = tor1_switch.get('serial_number') if tor1_switch else None
            else:
                tor1_po = None
                tor1_serial = None

            leaf2_po = None
            leaf2_serial = ''
            if leaf_is_vpc and leaf2_switch:
                leaf2_po = self._resolve_port_channel_id(parent_leaf2, leaf2_switch, errors)
                leaf2_serial = leaf2_switch.get('serial_number') if leaf2_switch else ''

            tor2_po = None
            tor2_serial = ''
            if tor_is_vpc and tor2_switch:
                tor2_po = self._resolve_port_channel_id(tor2, tor2_switch, errors)
                tor2_serial = tor2_switch.get('serial_number') if tor2_switch else ''

            required_serials = [leaf1_serial, tor1_serial]
            if any(serial is None for serial in required_serials):
                errors.append(
                    f"Serial numbers must be defined for all ToR pairing members. Pairing '{pairing_id}' is missing values."
                )

            if scenario != 'leaf_standalone_tor_standalone' and not leaf_is_vpc:
                # scenario with additional members but no vpc support already logged
                continue

            po_map = {}
            if leaf1_serial and leaf1_po is not None:
                po_map[f"{leaf1_serial}_PO"] = str(leaf1_po)
            if leaf2_serial and leaf2_po is not None:
                po_map[f"{leaf2_serial}_PO"] = str(leaf2_po)
            if tor1_serial and tor1_po is not None:
                po_map[f"{tor1_serial}_PO"] = str(tor1_po)
            if tor2_serial and tor2_po is not None:
                po_map[f"{tor2_serial}_PO"] = str(tor2_po)
            if leaf_is_vpc and leaf1_serial and leaf2_serial and leaf_vpc_domain:
                po_map[f"{leaf1_serial}~{leaf2_serial}_VPC"] = str(leaf_vpc_domain)
            if tor_is_vpc and tor1_serial and tor2_serial and tor_vpc_domain:
                po_map[f"{tor1_serial}~{tor2_serial}_VPC"] = str(tor_vpc_domain)

            if not po_map:
                errors.append(
                    f"No port-channel mapping could be derived for ToR pairing '{pairing_id}'."
                )
                continue

            if len(errors) > error_count_start:
                continue

            processed_pairs.append({
                'pairing_id': pairing_id,
                'scenario': scenario,
                'payload': {
                    'leafSN1': leaf1_serial or '',
                    'leafSN2': leaf2_serial or '',
                    'torSN1': tor1_serial or '',
                    'torSN2': tor2_serial or ''
                },
                'po_map': po_map
            })

        if errors:
            results['failed'] = True
            results['msg'] = '\n'.join(errors)
            return results

        model_data['vxlan']['topology']['tor_pairing'] = processed_pairs
        results['model_extended'] = model_data
        return results

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


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = ['vxlan', 'topology', 'tor_peers']

    def _get_switch(self, name, expected_role, switches, errors):
        """
        Get switch from switches map.
        Note: Basic validation is now handled by validation rule 312.
        This method focuses on data retrieval for payload generation.
        """
        switch = switches.get(name)
        if not switch:
            # Validation rule should have caught this
            errors.append(f"Switch '{name}' referenced in tor_peers is not defined in vxlan.topology.switches")
            return None
        return switch

    def _normalize_vpc_id(self, value, label, errors):
        if value is None:
            errors.append(f"{label} is required when defining tor pairing entries.")
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            errors.append(f"{label} must be an integer value. Current value: {value!r}")
            return None

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

    def _detect_scenario(self, peer, topology):
        """
        Auto-detect ToR pairing scenario based on configuration.

        Returns: tuple (scenario, leaf_vpc_domain, tor_vpc_domain)
        """
        parent_leaf1 = peer.get('parent_leaf1')
        parent_leaf2 = peer.get('parent_leaf2')
        tor1 = peer.get('tor1')
        tor2 = peer.get('tor2')

        # Simple string handling (new model)
        leaf1_name = parent_leaf1 if isinstance(parent_leaf1, str) else parent_leaf1.get('name')
        leaf2_name = parent_leaf2 if isinstance(parent_leaf2, str) else parent_leaf2.get('name') if parent_leaf2 else None
        tor1_name = tor1 if isinstance(tor1, str) else tor1.get('name')
        tor2_name = tor2 if isinstance(tor2, str) else tor2.get('name') if tor2 else None

        # Auto-resolve VPC domains from vpc_peers
        leaf_vpc_domain = self._resolve_vpc_domain_auto(leaf1_name, leaf2_name, topology) if leaf2_name else None
        tor_vpc_domain = self._resolve_vpc_domain_auto(tor1_name, tor2_name, topology) if tor2_name else None

        # Determine scenario
        if leaf2_name and tor2_name:
            if not leaf_vpc_domain or not tor_vpc_domain:
                return None, None, None  # Invalid configuration
            return 'vpc_to_vpc', leaf_vpc_domain, tor_vpc_domain
        elif leaf2_name and not tor2_name:
            if not leaf_vpc_domain:
                return None, None, None  # Invalid configuration
            return 'vpc_to_standalone', leaf_vpc_domain, None
        elif not leaf2_name and not tor2_name:
            return 'standalone_to_standalone', None, None
        else:
            # Unsupported: standalone leaf with vpc tor
            return None, None, None

    def _resolve_vpc_domain_auto(self, switch1_name, switch2_name, topology):
        """
        Auto-resolve VPC domain ID from vpc_peers configuration.
        """
        if not (switch1_name and switch2_name):
            return None

        vpc_peers = topology.get('vpc_peers', [])
        for vpc_pair in vpc_peers:
            peer1 = vpc_pair.get('peer1')
            peer2 = vpc_pair.get('peer2')
            if {peer1, peer2} == {switch1_name, switch2_name}:
                return vpc_pair.get('domain_id')
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

            # Handle both dict and string formats for switch references
            leaf1_name = parent_leaf1.get('name') if isinstance(parent_leaf1, dict) else parent_leaf1
            tor1_name = tor1.get('name') if isinstance(tor1, dict) else tor1
            leaf1_switch = self._get_switch(leaf1_name, 'leaf', switches, errors)
            tor1_switch = self._get_switch(tor1_name, 'tor', switches, errors)

            parent_leaf2 = peer.get('parent_leaf2')
            tor2 = peer.get('tor2')

            # Handle both dict and string formats for optional switches
            leaf2_name = parent_leaf2.get('name') if isinstance(parent_leaf2, dict) else parent_leaf2 if parent_leaf2 else None
            tor2_name = tor2.get('name') if isinstance(tor2, dict) else tor2 if tor2 else None

            leaf2_switch = None
            tor2_switch = None

            if parent_leaf2:
                leaf2_switch = self._get_switch(leaf2_name, 'leaf', switches, errors)
            if tor2:
                tor2_switch = self._get_switch(tor2_name, 'tor', switches, errors)

            # Auto-detect VPC scenarios based on presence of tor2/leaf2
            # No need for explicit tor_vpc_peer flag with new simplified model
            
            # Auto-resolve VPC domain IDs from vpc_peers configuration
            leaf_vpc_domain = self._resolve_vpc_domain(peer, 'leaf_vpc_id', leaf1_name, leaf2_name, topology)
            tor_vpc_domain = self._resolve_vpc_domain(peer, 'tor_vpc_id', tor1_name, tor2_name, topology)

            # Determine if this is a VPC scenario based on switch definitions
            leaf_is_vpc = bool(leaf2_switch and leaf_vpc_domain)
            tor_is_vpc = bool(tor2_switch and tor_vpc_domain)

            # Validate VPC domain IDs are present when needed
            if parent_leaf2 and not leaf_vpc_domain:
                errors.append(
                    f"tor_peers entry referencing leaves '{leaf1_name}' and '{leaf2_name}' requires a vPC domain ID. "
                    f"Ensure these switches are defined in vxlan.topology.vpc_peers."
                )
            if tor2 and not tor_vpc_domain:
                errors.append(
                    f"tor_peers entry referencing tors '{tor1_name}' and '{tor2_name}' requires a vPC domain ID. "
                    f"Ensure these switches are defined in vxlan.topology.vpc_peers."
                )

            # Determine scenario based on configuration
            scenario = 'standalone_to_standalone'
            if leaf_is_vpc and tor_is_vpc:
                scenario = 'vpc_to_vpc'
            elif leaf_is_vpc and not tor_is_vpc:
                scenario = 'vpc_to_standalone'
            elif not leaf_is_vpc and tor_is_vpc:
                errors.append(
                    f"Unsupported ToR pairing scenario: ToR vPC with standalone leaf for '{tor1_name}'. "
                    f"ToR vPC requires both parent_leaf1 and parent_leaf2 to be defined."
                )

            pairing_id = peer.get('pairing_id') or f"{leaf1_name}-{tor1_name}"
            if pairing_id in pairing_ids:
                errors.append(f"Duplicate tor pairing identifier '{pairing_id}' detected")
            pairing_ids.add(pairing_id)

            # Collect serial numbers
            if leaf1_switch:
                leaf1_serial = leaf1_switch.get('serial_number')
            else:
                leaf1_serial = None

            if tor1_switch:
                tor1_serial = tor1_switch.get('serial_number')
            else:
                tor1_serial = None

            # For VPC scenarios, normalize VPC domain IDs
            # Only normalize if we actually have a VPC (domain_id exists)
            leaf1_po = None
            leaf2_po = None
            tor1_po = None
            tor2_po = None
            
            if leaf_is_vpc:
                leaf1_po = self._normalize_vpc_id(leaf_vpc_domain, "leaf_vpc_id", errors)
                leaf2_po = leaf1_po  # Same VPC domain for both leafs
            
            if tor_is_vpc:
                tor1_po = self._normalize_vpc_id(tor_vpc_domain, "tor_vpc_id", errors)
                tor2_po = tor1_po  # Same VPC domain for both tors

            leaf2_serial = ''
            if leaf_is_vpc and leaf2_switch:
                leaf2_serial = leaf2_switch.get('serial_number') or ''

            tor2_serial = ''
            if tor_is_vpc and tor2_switch:
                tor2_serial = tor2_switch.get('serial_number') or ''

            required_serials = [leaf1_serial, tor1_serial]
            if any(serial is None for serial in required_serials):
                errors.append(
                    f"Serial numbers must be defined for all ToR pairing members. Pairing '{pairing_id}' is missing values."
                )

            # Skip if scenario validation already failed
            if scenario != 'standalone_to_standalone' and not leaf_is_vpc:
                # scenario with additional members but no vpc support already logged
                continue

            # po_map = {}
            # if leaf1_serial and leaf1_po is not None:
            #     po_map[f"{leaf1_serial}_PO"] = str(leaf1_po)
            # if leaf2_serial and leaf2_po is not None:
            #     po_map[f"{leaf2_serial}_PO"] = str(leaf2_po)
            # if tor1_serial and tor1_po is not None:
            #     po_map[f"{tor1_serial}_PO"] = str(tor1_po)
            # if tor2_serial and tor2_po is not None:
            #     po_map[f"{tor2_serial}_PO"] = str(tor2_po)
            # if leaf_is_vpc and leaf1_serial and leaf2_serial and leaf_vpc_domain:
            #     po_map[f"{leaf1_serial}~{leaf2_serial}_VPC"] = str(leaf_vpc_domain)
            # if tor_is_vpc and tor1_serial and tor2_serial and tor_vpc_domain:
            #     po_map[f"{tor1_serial}~{tor2_serial}_VPC"] = str(tor_vpc_domain)

            # # For standalone-to-standalone scenario, po_map can be empty (no VPC/port-channel needed)
            # if not po_map and scenario != 'standalone_to_standalone':
            #     errors.append(
            #         f"No port-channel mapping could be derived for ToR pairing '{pairing_id}'."
            #     )
            #     continue

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
                }
                # 'po_map': po_map
            })

        if errors:
            results['failed'] = True
            results['msg'] = '\n'.join(errors)
            return results

        model_data['vxlan']['topology']['tor_pairing'] = processed_pairs
        results['model_extended'] = model_data
        return results

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
    """
    ToR Pairing Prepare Plugin.
    
    Transforms user YAML configuration into NDFC API payloads and optionally
    performs diff detection for removal scenarios.
    
    """
    
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = ['vxlan', 'topology', 'tor_peers']

    def _normalize_serials(self, payload):
        """
        Create order-independent serial tuple for comparison.
        
        Handles VPC pairs where serial numbers can appear in any order
        between NDFC response and prepare plugin output.
        
        Args:
            payload: dict with leafSN1, leafSN2, torSN1, torSN2 keys
            
        Returns:
            tuple: ((sorted_tor_serials), (sorted_leaf_serials))
        """
        # Extract and filter empty strings
        tor_serials = [
            payload.get('torSN1', ''),
            payload.get('torSN2', '')
        ]
        tor_serials = [s for s in tor_serials if s]
        
        leaf_serials = [
            payload.get('leafSN1', ''),
            payload.get('leafSN2', '')
        ]
        leaf_serials = [s for s in leaf_serials if s]
        
        # Sort for order-independent comparison
        return (tuple(sorted(tor_serials)), tuple(sorted(leaf_serials)))

    def _get_switch(self, name, expected_role, switches, errors):
        """
        Get switch from switches map.
        This method focuses on data retrieval for payload generation.
        """
        switch = switches.get(name)
        if not switch:
            # Validation rule #311 should have caught this
            errors.append(f"Switch '{name}' referenced in tor_peers is not defined in vxlan.topology.switches")
            return None
        return switch

    # DELETE ME LATER - rule #311 checks VPC
    def _normalize_vpc_id(self, value, label, errors):
        if value is None:
            errors.append(f"{label} is required when defining tor pairing entries.")
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            errors.append(f"{label} must be an integer value. Current value: {value!r}")
            return None

    # DELETE ME LATER - rule #311 checks VPC
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
        """
        Main prepare method - transforms user config to API payloads and performs diff detection.
        
        Returns:
        dict: results with model_extended updated and optional metadata
            - model_extended['vxlan']['topology']['tor_pairing']: current pairings
            - model_extended['vxlan']['topology']['tor_pairing_removed']: removals
            - results['tor_pairing_diff_stats']: debug statistics (when previous state supplied)
            or results['failed'] = True with aggregated error messages
        Examples:
        [
            {
                'pairing_id': 'LEAF_11-TOR_24',
                'scenario': 'vpc_to_vpc',
                'payload': {
                    'leafSN1': '9BUXESV382R',
                    'leafSN2': '99FYP2OV1NS',
                    'torSN1': '9Q2X9XATUNL',
                    'torSN2': '9M81OZOOCWM'
                }
            }
        ]
        
        """
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
                }
                # 'po_map': po_map
            })

        if errors:
            results['failed'] = True
            results['msg'] = '\n'.join(errors)
            return results
        
        #############################################
        ## Diff Detection for ToR Pairing Removals ##
        #############################################

        # Store processed pairings in model_extended
        model_data['vxlan']['topology']['tor_pairing'] = processed_pairs
        
        # Perform diff detection for removals
        # Get previous pairings (passed from ndfc_tor_pairing.yml)
        previous_pairings = self.kwargs.get('tor_pairing_previous_list', [])
        
        if previous_pairings:
            # Build lookup set of current pairing serials
            current_serial_sets = {}
            for pairing in processed_pairs:
                serial_key = self._normalize_serials(pairing['payload'])
                current_serial_sets[serial_key] = pairing
            
            # Find removals by checking which previous pairings no longer exist
            removed = []
            for prev_pairing in previous_pairings:
                prev_serial_key = self._normalize_serials(prev_pairing['payload'])
                if prev_serial_key not in current_serial_sets:
                    removed.append(prev_pairing)
            
            # Store results in model_extended for downstream tasks
            model_data['vxlan']['topology']['tor_pairing_removed'] = removed
            
            # Add debug information
            results['tor_pairing_diff_stats'] = {
                'previous_count': len(previous_pairings),
                'current_count': len(processed_pairs),
                'removed_count': len(removed),
                'previous_ids': [p.get('pairing_id', 'unknown') for p in previous_pairings],
                'current_ids': [p.get('pairing_id', 'unknown') for p in processed_pairs],
                'removed_ids': [p.get('pairing_id', 'unknown') for p in removed]
            }
        else:
            # No previous state, nothing to remove
            model_data['vxlan']['topology']['tor_pairing_removed'] = []
        
        results['model_extended'] = model_data
        return results

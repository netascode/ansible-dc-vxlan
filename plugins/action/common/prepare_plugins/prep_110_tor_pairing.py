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

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
action: prep_110_tor_pairing
short_description: Prepare ToR pairing
description:
  - Prepare ToR pairing
options: {}
author:
  - Cisco
'''

EXAMPLES = r'''
'''

RETURN = r'''
'''


class PreparePlugin:
    """
    ToR Pairing Prepare Plugin.

    Transforms user YAML configuration (tor_peers) into NDFC API payloads.

    This plugin runs during the validation/prepare phase to:
    - Resolve switch names to serial numbers
    - Auto-detect VPC scenarios based on configuration
    - Build standardized payload format for NDFC API calls

    Note: Diff detection for removals is handled separately by the
    process_tor_pairing action plugin's 'diff' operation.
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = ['vxlan', 'topology', 'tor_peers']

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

        # Store processed pairings in model_extended for downstream tasks
        model_data['vxlan']['topology']['tor_pairing'] = processed_pairs

        results['model_extended'] = model_data
        return results

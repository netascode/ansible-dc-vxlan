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
    Compares previous and current ToR pairings to determine removals.
    Handles order-independent serial number matching for brownfield scenarios.
    
    This plugin runs after prep_110_tor_pairing.py and performs efficient
    diff detection using normalized serial number sets.
    """
    
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = ['vxlan', 'topology', 'tor_pairing']
    
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
    
    def prepare(self):
        """
        Compare current and previous ToR pairings to identify removals.
        
        Previous pairings come from:
        1. Artifact .old file (normal workflow)
        2. NDFC API discovery (brownfield mode)
        
        Current pairings come from prep_110_tor_pairing.py output.
        
        Returns:
            results dict with tor_pairing_removed added to model_extended
        """
        results = self.kwargs['results']
        model_data = results.get('model_extended', {})
        
        # Get current pairings from prep_110_tor_pairing output
        topology = model_data.get('vxlan', {}).get('topology', {})
        current_pairings = topology.get('tor_pairing', [])
        
        # Get previous pairings (passed from ndfc_tor_pairing.yml)
        previous_pairings = self.kwargs.get('tor_pairing_previous_list', [])
        
        if not previous_pairings:
            # No previous state, nothing to remove
            topology['tor_pairing_removed'] = []
            results['model_extended'] = model_data
            return results
        
        # Build lookup set of current pairing serials
        current_serial_sets = {}
        for pairing in current_pairings:
            serial_key = self._normalize_serials(pairing['payload'])
            current_serial_sets[serial_key] = pairing
        
        # Find removals by checking which previous pairings no longer exist
        removed = []
        for prev_pairing in previous_pairings:
            prev_serial_key = self._normalize_serials(prev_pairing['payload'])
            if prev_serial_key not in current_serial_sets:
                removed.append(prev_pairing)
        
        # Store results in model_extended for downstream tasks
        topology['tor_pairing_removed'] = removed
        results['model_extended'] = model_data
        
        # Add debug information
        results['tor_pairing_diff_stats'] = {
            'previous_count': len(previous_pairings),
            'current_count': len(current_pairings),
            'removed_count': len(removed),
            'previous_ids': [p.get('pairing_id', 'unknown') for p in previous_pairings],
            'current_ids': [p.get('pairing_id', 'unknown') for p in current_pairings],
            'removed_ids': [p.get('pairing_id', 'unknown') for p in removed]
        }
        
        return results

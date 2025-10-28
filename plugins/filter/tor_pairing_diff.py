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


def normalize_serials(payload):
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


def tor_pairing_diff(current_pairings, previous_pairings):
    """
    Compare current and previous ToR pairings to identify removals.
    
    Uses order-independent serial number matching to correctly identify
    pairings that should be removed (exist in previous but not in current).
    
    Performance: O(n+m) where n=current count, m=previous count
    (vs O(n*m) for nested loop approach)
    
    Args:
        current_pairings: list of current ToR pairing dicts
        previous_pairings: list of previous ToR pairing dicts
        
    Returns:
        dict with keys:
            - removed: list of pairings to remove
            - stats: dict with counts and IDs for debugging
    """
    if not previous_pairings:
        return {
            'removed': [],
            'stats': {
                'previous_count': 0,
                'current_count': len(current_pairings),
                'removed_count': 0
            }
        }
    
    # Build lookup set of current pairing serials
    # Time complexity: O(n) where n = current pairing count
    current_serial_sets = {}
    for pairing in current_pairings:
        serial_key = normalize_serials(pairing['payload'])
        current_serial_sets[serial_key] = pairing
    
    # Find removals by checking which previous pairings no longer exist
    # Time complexity: O(m) where m = previous pairing count
    removed = []
    for prev_pairing in previous_pairings:
        prev_serial_key = normalize_serials(prev_pairing['payload'])
        if prev_serial_key not in current_serial_sets:
            removed.append(prev_pairing)
    
    # Return results with statistics for debugging
    return {
        'removed': removed,
        'stats': {
            'previous_count': len(previous_pairings),
            'current_count': len(current_pairings),
            'removed_count': len(removed),
            'previous_ids': [p.get('pairing_id', 'unknown') for p in previous_pairings],
            'current_ids': [p.get('pairing_id', 'unknown') for p in current_pairings],
            'removed_ids': [p.get('pairing_id', 'unknown') for p in removed]
        }
    }


class FilterModule(object):
    """Ansible filter plugin for ToR pairing diff operations."""
    
    def filters(self):
        return {
            'tor_pairing_diff': tor_pairing_diff,
            'normalize_tor_serials': normalize_serials
        }

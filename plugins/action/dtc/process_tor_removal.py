# Copyright (c) 2025 Cisco Systems, Inc. and its affiliates
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

from __future__ import absolute_import, division, print_function


__metaclass__ = type

from ansible.plugins.action import ActionBase  # type: ignore
import json
from urllib.parse import quote


class TorRemovalProcessor:
    """
    Process TOR pairing removal list and build NDFC API query parameters.

    This processor takes a list of TOR pairings to be removed and transforms
    each into the proper NDFC API DELETE query format.
    """

    def __init__(self, params):
        """
        Initialize the TOR removal processor.

        Args:
            params: Dictionary containing:
                - tor_pairing_removed: List of TOR pairing dicts to be removed
                - fabric_name: Name of the fabric
        """
        self.class_name = self.__class__.__name__
        self.tor_pairing_removed = params.get('tor_pairing_removed', [])
        self.fabric_name = params.get('fabric_name', '')
        self.removal_operations = []

    def _build_leaftor_query(self, payload):
        """
        Build the leaftor query parameter for NDFC DELETE API.

        The NDFC API expects a URL-encoded JSON dict where:
        - Keys are leaf serial numbers
        - Values are comma-separated TOR serial numbers
        - Example: {"leafSN1": "torSN1,torSN2", "leafSN2": "torSN1,torSN2"}

        Args:
            payload: Dictionary containing leafSN1, leafSN2, torSN1, torSN2

        Returns:
            str: URL-encoded JSON query string
        """
        # Step 1: Build TOR serial list (filter empty strings)
        tor_serials = []
        if payload.get('torSN1'):
            tor_serials.append(payload['torSN1'])
        if payload.get('torSN2'):
            tor_serials.append(payload['torSN2'])

        # Step 2: Join TORs with comma
        tor_string = ','.join(tor_serials)

        # Step 3: Build leaf serial list (filter empty strings)
        leaf_serials = []
        if payload.get('leafSN1'):
            leaf_serials.append(payload['leafSN1'])
        if payload.get('leafSN2'):
            leaf_serials.append(payload['leafSN2'])

        # Step 4: Create dict mapping each leaf to all tors
        leaftor_map = {}
        for leaf_sn in leaf_serials:
            leaftor_map[leaf_sn] = tor_string

        # Step 5: Convert to JSON and URL encode
        leaftor_json = json.dumps(leaftor_map)
        leaftor_query = quote(leaftor_json, safe='')

        return leaftor_query

    def _validate_payload(self, payload):
        """
        Validate that the payload has required serial numbers.

        Args:
            payload: Dictionary containing serial number fields

        Returns:
            bool: True if valid (has at least leafSN1 and torSN1)
        """
        return bool(payload.get('leafSN1') and payload.get('torSN1'))

    def process_removals(self):
        """
        Process all TOR pairings to be removed and build removal operations.

        Returns:
            list: List of removal operation dictionaries, each containing:
                - pairing_id: Identifier for the pairing
                - path: Full NDFC API DELETE path with query parameters
                - payload: Original payload (for reference)
        """
        for pairing in self.tor_pairing_removed:
            # Validate payload has required fields
            payload = pairing.get('payload', {})
            if not self._validate_payload(payload):
                # Skip invalid payloads (missing required serial numbers)
                continue

            # Build the leaftor query
            leaftor_query = self._build_leaftor_query(payload)

            # Build the full API path
            api_path = (
                f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/tor/"
                f"fabrics/{self.fabric_name}/switches/pair?leaftor={leaftor_query}"
            )

            # Create removal operation
            removal_op = {
                'pairing_id': pairing.get('pairing_id', 'unknown'),
                'path': api_path,
                'payload': payload,
                'scenario': pairing.get('scenario', 'unknown')
            }

            self.removal_operations.append(removal_op)

        return self.removal_operations


class ActionModule(ActionBase):
    """
    Ansible action plugin to process TOR pairing removals.

    This plugin takes a list of TOR pairings to be removed and generates
    the necessary NDFC API DELETE paths with proper query parameters.

    Usage:
        - name: Process TOR removal operations
          cisco.nac_dc_vxlan.dtc.process_tor_removal:
            tor_pairing_removed: "{{ vars_common_local.tor_pairing_removed }}"
            fabric_name: "{{ MD_Extended.vxlan.fabric.name }}"
          register: tor_removal_operations
    """

    def run(self, tmp=None, task_vars=None):
        """
        Execute the action plugin.

        Returns:
            dict: Results containing:
                - removal_operations: List of removal operation dicts
                - count: Number of removal operations
                - msg: Status message
        """
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False

        # Get parameters from task
        params = {
            'tor_pairing_removed': self._task.args.get('tor_pairing_removed', []),
            'fabric_name': self._task.args.get('fabric_name', '')
        }

        # Validate required parameters
        if not params['fabric_name']:
            results['failed'] = True
            results['msg'] = 'Missing required parameter: fabric_name'
            return results

        if not params['tor_pairing_removed']:
            results['removal_operations'] = []
            results['count'] = 0
            results['msg'] = 'No TOR pairings to remove'
            return results

        # Initialize processor
        processor = TorRemovalProcessor(params)

        # Process removals
        try:
            removal_operations = processor.process_removals()

            results['removal_operations'] = removal_operations
            results['count'] = len(removal_operations)
            results['msg'] = f'Prepared {len(removal_operations)} TOR pairing removal operation(s)'

        except Exception as e:
            results['failed'] = True
            results['msg'] = f'Failed to process TOR removals: {str(e)}'
            results['removal_operations'] = []
            results['count'] = 0

        return results

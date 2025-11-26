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

from ansible.plugins.action import ActionBase # type: ignore


class TorDiscoveryProcessor:
    """
    Process NDFC TOR pairing discovery API response and transform it into
    standardized format for artifact generation.
    """

    def __init__(self, params):
        """
        Initialize the TOR discovery processor.

        Args:
            params: Dictionary containing:
                - discovery_response: NDFC API response from tor discovery query
        """
        self.class_name = self.__class__.__name__
        self.discovery_response = params.get('discovery_response', {})
        self.discovered_pairings = []

    def _detect_scenario(self, tor_pair):
        """
        Detect the pairing scenario based on the NDFC response data.

        Args:
            tor_pair: Dictionary containing torName, torSN, leafSNs, torPeerSN, remarks

        Returns:
            str: 'vpc_to_vpc', 'vpc_to_standalone', or 'standalone_to_standalone'
        """
        tor_peer_sn = tor_pair.get('torPeerSN')
        leaf_sns = tor_pair.get('leafSNs') or ''

        # vpc_to_vpc: torPeerSN exists AND comma in leafSNs
        if tor_peer_sn is not None and ',' in leaf_sns:
            return 'vpc_to_vpc'

        # vpc_to_standalone: Comma in leafSNs BUT no torPeerSN
        if ',' in leaf_sns and tor_peer_sn is None:
            return 'vpc_to_standalone'

        # standalone_to_standalone: Neither condition met
        return 'standalone_to_standalone'

    def _parse_serial_numbers(self, tor_pair):
        """
        Parse and split serial numbers from NDFC response.

        Args:
            tor_pair: Dictionary containing torSN and leafSNs

        Returns:
            dict: Dictionary with leafSN1, leafSN2, torSN1, torSN2
        """
        leaf_sns = tor_pair.get('leafSNs') or ''
        tor_sn = tor_pair.get('torSN') or ''

        # Parse leaf serial numbers
        if leaf_sns and ',' in leaf_sns:
            leaf_parts = leaf_sns.split(',')
            leaf_sn1 = leaf_parts[0] if len(leaf_parts) > 0 else ''
            leaf_sn2 = leaf_parts[1] if len(leaf_parts) > 1 else ''
        else:
            leaf_sn1 = leaf_sns if leaf_sns else ''
            leaf_sn2 = ''

        # Parse TOR serial numbers
        if tor_sn and ',' in tor_sn:
            tor_parts = tor_sn.split(',')
            tor_sn1 = tor_parts[0] if len(tor_parts) > 0 else ''
            tor_sn2 = tor_parts[1] if len(tor_parts) > 1 else ''
        else:
            tor_sn1 = tor_sn if tor_sn else ''
            tor_sn2 = ''

        return {
            'leafSN1': leaf_sn1,
            'leafSN2': leaf_sn2,
            'torSN1': tor_sn1,
            'torSN2': tor_sn2
        }

    def _generate_pairing_id(self, tor_pair):
        tor_name = tor_pair.get('torName') or ''
        return tor_name.replace('~', '-')

    def _is_already_paired(self, tor_pair):
        remarks = tor_pair.get('remarks') or ''
        return 'Already paired' in remarks

    def process_discovery(self):
        """
        Process the NDFC discovery response and transform all TOR pairs.

        Returns:
            list: List of processed pairing dictionaries
        """
        # Extract torPairs from response
        tor_pairs = []
        if isinstance(self.discovery_response, dict):
            data = self.discovery_response.get('DATA', {})
            if isinstance(data, dict):
                tor_pairs = data.get('torPairs') or []

        # Process each TOR pair
        for tor_pair in tor_pairs:
            # Only process pairs that are already paired
            if not self._is_already_paired(tor_pair):
                continue

            # Generate pairing_id
            pairing_id = self._generate_pairing_id(tor_pair)

            # Detect scenario
            scenario = self._detect_scenario(tor_pair)

            # Parse serial numbers
            payload = self._parse_serial_numbers(tor_pair)

            # Build the processed pairing
            processed_pairing = {
                'pairing_id': pairing_id,
                'scenario': scenario,
                'payload': payload
            }

            self.discovered_pairings.append(processed_pairing)

        return self.discovered_pairings


class ActionModule(ActionBase):
    """
    Ansible action plugin to process NDFC TOR discovery response.

    Usage:
        - name: Process NDFC TOR discovery response
          cisco.nac_dc_vxlan.dtc.process_tor_discovery:
            discovery_response: "{{ ndfc_tor_discovery.response }}"
          register: tor_discovery_result
    """

    def run(self, tmp=None, task_vars=None):
        """
        Execute the action plugin.

        Returns:
            dict: Results containing:
                - discovered_pairings: List of processed pairing dictionaries
                - count: Number of pairings discovered
        """
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False

        # Get parameters from task
        params = {
            'discovery_response': self._task.args.get('discovery_response', {})
        }

        # Validate required parameters
        if not params['discovery_response']:
            results['discovered_pairings'] = []
            results['count'] = 0
            results['msg'] = 'No discovery response provided'
            return results

        # Initialize processor
        processor = TorDiscoveryProcessor(params)

        # Process discovery response
        try:
            discovered_pairings = processor.process_discovery()

            results['discovered_pairings'] = discovered_pairings
            results['count'] = len(discovered_pairings)
            results['msg'] = f'Successfully processed {len(discovered_pairings)} TOR pairing(s)'

        except Exception as e:
            results['failed'] = True
            results['msg'] = f'Failed to process TOR discovery: {str(e)}'
            results['discovered_pairings'] = []
            results['count'] = 0

        return results

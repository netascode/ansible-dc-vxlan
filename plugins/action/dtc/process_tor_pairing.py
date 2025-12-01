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

"""
Unified TOR Pairing Action Plugin for NDFC.

This module consolidates all TOR pairing operations (discovery, create, removal)
into a single action plugin that detects the calling role and delegates to the
appropriate processor class.

Supported operations:
    - discovery: Process NDFC TOR discovery API response
    - create: Prepare TOR pairing POST operations
    - remove: Prepare TOR pairing DELETE operations
"""

from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
from urllib.parse import quote

from ansible.plugins.action import ActionBase  # type: ignore


# =============================================================================
# TOR Discovery Processor
# =============================================================================

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
        """Generate a pairing ID from the TOR name."""
        tor_name = tor_pair.get('torName') or ''
        return tor_name.replace('~', '-')

    def _is_already_paired(self, tor_pair):
        """Check if the TOR pair is already paired based on remarks."""
        remarks = tor_pair.get('remarks') or ''
        return 'Already paired' in remarks

    def process(self):
        """
        Process the NDFC discovery response and transform all TOR pairs.

        Returns:
            dict: Results containing discovered_pairings and count
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

        return {
            'discovered_pairings': self.discovered_pairings,
            'count': len(self.discovered_pairings),
            'msg': f'Successfully processed {len(self.discovered_pairings)} TOR pairing(s)'
        }


# =============================================================================
# TOR Create Processor
# =============================================================================

class TorCreateProcessor:
    """
    Process TOR pairing create list and prepare NDFC API POST operations.

    This processor takes a list of TOR pairings to be created and validates
    each one before preparing it for the NDFC API POST call.
    """

    def __init__(self, params):
        """
        Initialize the TOR create processor.

        Args:
            params: Dictionary containing:
                - tor_pairing: List of TOR pairing dicts to be created
                - fabric_name: Name of the fabric
        """
        self.class_name = self.__class__.__name__
        self.tor_pairing = params.get('tor_pairing', [])
        self.fabric_name = params.get('fabric_name', '')
        self.create_operations = []

    def _validate_payload(self, payload):
        """
        Validate that the payload has required serial numbers.

        Args:
            payload: Dictionary containing serial number fields

        Returns:
            bool: True if valid (has at least leafSN1 and torSN1)
        """
        return bool(payload.get('leafSN1') and payload.get('torSN1'))

    def process(self):
        """
        Process all TOR pairings to be created and build create operations.

        Returns:
            dict: Results containing create_operations and count
        """
        for pairing in self.tor_pairing:
            # Validate payload has required fields
            payload = pairing.get('payload', {})
            if not self._validate_payload(payload):
                # Skip invalid payloads (missing required serial numbers)
                continue

            # Build the API path
            api_path = (
                f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/tor/"
                f"fabrics/{self.fabric_name}/switches/pair/custom-id"
            )

            # Convert payload to JSON string
            json_data = json.dumps(payload)

            # Create operation
            create_op = {
                'pairing_id': pairing.get('pairing_id', 'unknown'),
                'path': api_path,
                'json_data': json_data,
                'payload': payload,
                'scenario': pairing.get('scenario', 'unknown')
            }

            self.create_operations.append(create_op)

        return {
            'create_operations': self.create_operations,
            'count': len(self.create_operations),
            'msg': f'Prepared {len(self.create_operations)} TOR pairing create operation(s)'
        }


# =============================================================================
# TOR Removal Processor
# =============================================================================

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

    def process(self):
        """
        Process all TOR pairings to be removed and build removal operations.

        Returns:
            dict: Results containing removal_operations and count
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

        return {
            'removal_operations': self.removal_operations,
            'count': len(self.removal_operations),
            'msg': f'Prepared {len(self.removal_operations)} TOR pairing removal operation(s)'
        }


# =============================================================================
# Unified Action Module
# =============================================================================

class ActionModule(ActionBase):
    """
    Unified Ansible action plugin for TOR pairing operations.

    This plugin automatically detects the operation type based on the Ansible
    role path or explicit 'operation' parameter, then delegates to the
    appropriate processor class.

    Operation Detection:
        1. Explicit 'operation' parameter: 'discovery', 'create', or 'remove'
        2. Role path detection:
           - 'dtc/common' or 'dtc/create' → 'discovery' or 'create' based on params
           - 'dtc/remove' → 'remove'

    Usage Examples:

        # Discovery (auto-detected from role or explicit)
        - name: Process NDFC TOR discovery response
          cisco.nac_dc_vxlan.dtc.process_tor_pairing:
            operation: discovery
            discovery_response: "{{ ndfc_tor_discovery.response }}"
          register: tor_discovery_result

        # Create (auto-detected from role or explicit)
        - name: Process TOR create operations
          cisco.nac_dc_vxlan.dtc.process_tor_pairing:
            operation: create
            tor_pairing: "{{ vars_common_local.tor_pairing }}"
            fabric_name: "{{ MD_Extended.vxlan.fabric.name }}"
          register: tor_create_operations

        # Remove (auto-detected from role or explicit)
        - name: Process TOR removal operations
          cisco.nac_dc_vxlan.dtc.process_tor_pairing:
            operation: remove
            tor_pairing_removed: "{{ vars_common_local.tor_pairing_removed }}"
            fabric_name: "{{ MD_Extended.vxlan.fabric.name }}"
          register: tor_removal_operations
    """

    # Mapping of operations to processor classes
    PROCESSORS = {
        'discovery': TorDiscoveryProcessor,
        'create': TorCreateProcessor,
        'remove': TorRemovalProcessor,
    }

    def _detect_operation(self, task_vars):
        """
        Detect the operation type from explicit parameter or role path.

        Args:
            task_vars: Ansible task variables

        Returns:
            str: Operation type ('discovery', 'create', 'remove') or None
        """
        # Check for explicit operation parameter first
        explicit_op = self._task.args.get('operation')
        if explicit_op and explicit_op in self.PROCESSORS:
            return explicit_op

        # Try to detect from role path
        role_path = task_vars.get('role_path', '') if task_vars else ''

        if 'dtc/remove' in role_path:
            return 'remove'
        elif 'dtc/create' in role_path:
            # In create role, check which params are provided
            if self._task.args.get('tor_pairing'):
                return 'create'
            elif self._task.args.get('discovery_response'):
                return 'discovery'
        elif 'dtc/common' in role_path:
            # In common role, discovery is typically called
            if self._task.args.get('discovery_response'):
                return 'discovery'

        # Fallback: detect based on which parameters are provided
        if self._task.args.get('discovery_response'):
            return 'discovery'
        elif self._task.args.get('tor_pairing'):
            return 'create'
        elif self._task.args.get('tor_pairing_removed'):
            return 'remove'

        return None

    def _build_params(self, operation):
        """
        Build the parameter dictionary for the processor.

        Args:
            operation: The detected operation type

        Returns:
            dict: Parameters for the processor
        """
        if operation == 'discovery':
            return {
                'discovery_response': self._task.args.get('discovery_response', {})
            }
        elif operation == 'create':
            return {
                'tor_pairing': self._task.args.get('tor_pairing', []),
                'fabric_name': self._task.args.get('fabric_name', '')
            }
        elif operation == 'remove':
            return {
                'tor_pairing_removed': self._task.args.get('tor_pairing_removed', []),
                'fabric_name': self._task.args.get('fabric_name', '')
            }
        return {}

    def _validate_params(self, operation, params):
        """
        Validate required parameters for the operation.

        Args:
            operation: The operation type
            params: The parameter dictionary

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        if operation == 'discovery':
            if not params.get('discovery_response'):
                return False, 'No discovery response provided'
        elif operation == 'create':
            if not params.get('fabric_name'):
                return False, 'Missing required parameter: fabric_name'
            if not params.get('tor_pairing'):
                return True, None  # Empty list is valid, just no work to do
        elif operation == 'remove':
            if not params.get('fabric_name'):
                return False, 'Missing required parameter: fabric_name'
            if not params.get('tor_pairing_removed'):
                return True, None  # Empty list is valid, just no work to do

        return True, None

    def run(self, tmp=None, task_vars=None):
        """
        Execute the action plugin.

        Detects the operation type, validates parameters, and delegates
        to the appropriate processor class.

        Returns:
            dict: Results from the processor, containing operation-specific data
        """
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False

        # Detect operation type
        operation = self._detect_operation(task_vars)
        if not operation:
            results['failed'] = True
            results['msg'] = (
                "Could not detect operation type. Provide 'operation' parameter "
                "(discovery, create, remove) or ensure appropriate input parameters "
                "(discovery_response, tor_pairing, tor_pairing_removed) are set."
            )
            return results

        results['operation'] = operation

        # Build parameters for the processor
        params = self._build_params(operation)

        # Validate parameters
        is_valid, error_msg = self._validate_params(operation, params)
        if not is_valid:
            results['failed'] = True
            results['msg'] = error_msg
            return results

        # Handle empty input cases (valid but no work to do)
        if operation == 'create' and not params.get('tor_pairing'):
            results['create_operations'] = []
            results['count'] = 0
            results['msg'] = 'No TOR pairings to create'
            return results

        if operation == 'remove' and not params.get('tor_pairing_removed'):
            results['removal_operations'] = []
            results['count'] = 0
            results['msg'] = 'No TOR pairings to remove'
            return results

        if operation == 'discovery' and not params.get('discovery_response'):
            results['discovered_pairings'] = []
            results['count'] = 0
            results['msg'] = 'No discovery response provided'
            return results

        # Get the processor class and instantiate
        processor_class = self.PROCESSORS[operation]
        processor = processor_class(params)

        # Process and return results
        try:
            processor_results = processor.process()
            results.update(processor_results)
        except Exception as e:
            results['failed'] = True
            results['msg'] = f'Failed to process TOR {operation}: {str(e)}'
            # Set empty result keys based on operation
            if operation == 'discovery':
                results['discovered_pairings'] = []
            elif operation == 'create':
                results['create_operations'] = []
            elif operation == 'remove':
                results['removal_operations'] = []
            results['count'] = 0

        return results

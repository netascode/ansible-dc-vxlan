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
into a single action plugin that handles both data processing and NDFC API calls.

Supported operations:
    - discovery: Query NDFC for existing TOR pairings and process the response
    - create: Create TOR pairings via NDFC POST API
    - remove: Remove TOR pairings via NDFC DELETE API
"""

from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
from urllib.parse import quote

from ansible.plugins.action import ActionBase  # type: ignore
from ansible.utils.display import Display

display = Display()


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
    Process TOR pairing create list and prepare/execute NDFC API POST operations.
    """

    def __init__(self, params):
        """
        Initialize the TOR create processor.

        Args:
            params: Dictionary containing:
                - tor_pairing: List of TOR pairing dicts to be created
                - fabric_name: Name of the fabric
        """
        self.tor_pairing = params.get('tor_pairing', [])
        self.fabric_name = params.get('fabric_name', '')

    def _validate_payload(self, payload):
        """
        Validate that the payload has required serial numbers.

        Args:
            payload: Dictionary containing serial number fields

        Returns:
            bool: True if valid (has at least leafSN1 and torSN1)
        """
        return bool(payload.get('leafSN1') and payload.get('torSN1'))

    def build_operations(self):
        """
        Build the list of create operations without executing them.

        Returns:
            list: List of create operation dictionaries
        """
        create_operations = []

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

            # Create operation
            create_op = {
                'pairing_id': pairing.get('pairing_id', 'unknown'),
                'path': api_path,
                'payload': payload,
                'scenario': pairing.get('scenario', 'unknown')
            }

            create_operations.append(create_op)

        return create_operations


# =============================================================================
# TOR Removal Processor
# =============================================================================

class TorRemovalProcessor:
    """
    Process TOR pairing removal list and prepare/execute NDFC API DELETE operations.
    """

    def __init__(self, params):
        """
        Initialize the TOR removal processor.

        Args:
            params: Dictionary containing:
                - tor_pairing_removed: List of TOR pairing dicts to be removed
                - fabric_name: Name of the fabric
        """
        self.tor_pairing_removed = params.get('tor_pairing_removed', [])
        self.fabric_name = params.get('fabric_name', '')

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

    def build_operations(self):
        """
        Build the list of removal operations without executing them.

        Returns:
            list: List of removal operation dictionaries
        """
        removal_operations = []

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

            removal_operations.append(removal_op)

        return removal_operations


# =============================================================================
# Unified Action Module
# =============================================================================

class ActionModule(ActionBase):
    """
    Unified Ansible action plugin for TOR pairing operations.

    This plugin handles both data processing and NDFC API execution for TOR
    pairing operations. It can operate in two modes:

    1. **Prepare mode** (execute_api=false, default for backwards compatibility):
       Only prepares the operations and returns them for external execution.

    2. **Execute mode** (execute_api=true):
       Prepares AND executes the NDFC API calls directly.

    Operations:
        - discovery: Query NDFC for existing TOR pairings
        - create: Create TOR pairings via POST
        - remove: Delete TOR pairings via DELETE

    Usage Examples:

        # Discovery - Query NDFC and process response
        - name: Discover existing TOR pairings from NDFC
          cisco.nac_dc_vxlan.dtc.process_tor_pairing:
            operation: discovery
            fabric_name: "{{ MD_Extended.vxlan.fabric.name }}"
            leaf_serial_number: "{{ leaf_switches_for_query[0].serial_number }}"
          register: tor_discovery_result

        # Discovery - Process existing response (backwards compatible)
        - name: Process NDFC TOR discovery response
          cisco.nac_dc_vxlan.dtc.process_tor_pairing:
            operation: discovery
            discovery_response: "{{ ndfc_tor_discovery.response }}"
          register: tor_discovery_result

        # Create - Execute API calls directly
        - name: Create TOR pairings in NDFC
          cisco.nac_dc_vxlan.dtc.process_tor_pairing:
            operation: create
            tor_pairing: "{{ vars_common_local.tor_pairing }}"
            fabric_name: "{{ MD_Extended.vxlan.fabric.name }}"
            execute_api: true
          register: tor_create_result

        # Remove - Execute API calls directly
        - name: Remove TOR pairings from NDFC
          cisco.nac_dc_vxlan.dtc.process_tor_pairing:
            operation: remove
            tor_pairing_removed: "{{ vars_common_local.tor_pairing_removed }}"
            fabric_name: "{{ MD_Extended.vxlan.fabric.name }}"
            execute_api: true
          register: tor_remove_result
    """

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
        if explicit_op and explicit_op in ('discovery', 'create', 'remove'):
            return explicit_op

        # Try to detect from role path
        role_path = task_vars.get('role_path', '') if task_vars else ''

        if 'dtc/remove' in role_path:
            return 'remove'
        elif 'dtc/create' in role_path:
            if self._task.args.get('tor_pairing'):
                return 'create'
            elif self._task.args.get('discovery_response'):
                return 'discovery'
        elif 'dtc/common' in role_path:
            if self._task.args.get('discovery_response'):
                return 'discovery'
            elif self._task.args.get('leaf_serial_number'):
                return 'discovery'

        # Fallback: detect based on which parameters are provided
        if self._task.args.get('discovery_response'):
            return 'discovery'
        elif self._task.args.get('leaf_serial_number'):
            return 'discovery'
        elif self._task.args.get('tor_pairing'):
            return 'create'
        elif self._task.args.get('tor_pairing_removed'):
            return 'remove'

        return None

    def _execute_ndfc_rest(self, method, path, json_data=None, task_vars=None, tmp=None):
        """
        Execute an NDFC REST API call using cisco.dcnm.dcnm_rest module.

        Args:
            method: HTTP method (GET, POST, DELETE)
            path: API path
            json_data: Optional JSON payload for POST requests
            task_vars: Ansible task variables
            tmp: Temporary directory

        Returns:
            dict: Module execution result
        """
        module_args = {
            "method": method,
            "path": path,
        }

        # Use 'data' instead of 'json_data' for dcnm_rest module
        # This is the primary parameter name, json_data is just an alias
        if json_data is not None:
            module_args["data"] = json_data

        display.vvv(f"TOR API: Executing {method} {path} with args: {module_args}")

        result = self._execute_module(
            module_name="cisco.dcnm.dcnm_rest",
            module_args=module_args,
            task_vars=task_vars,
            tmp=tmp
        )

        display.vvv(f"TOR API: Result keys: {result.keys() if result else 'None'}")
        if result and result.get('failed'):
            display.vvv(f"TOR API: Full failure result: {result}")

        return result

    def _run_discovery(self, task_vars, tmp):
        """
        Execute TOR pairing discovery operation.

        If leaf_serial_number is provided, queries NDFC first.
        If discovery_response is provided, processes it directly.

        Returns:
            dict: Results with discovered_pairings
        """
        results = {
            'failed': False,
            'operation': 'discovery',
            'discovered_pairings': [],
            'count': 0
        }

        fabric_name = self._task.args.get('fabric_name', '')
        leaf_serial_number = self._task.args.get('leaf_serial_number', '')
        discovery_response = self._task.args.get('discovery_response')

        # If leaf_serial_number provided, query NDFC first
        if leaf_serial_number and fabric_name:
            api_path = (
                f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/tor/"
                f"fabrics/{fabric_name}/switches/{leaf_serial_number}"
            )

            display.v(f"TOR Discovery: Querying NDFC at {api_path}")

            ndfc_result = self._execute_ndfc_rest(
                method="GET",
                path=api_path,
                task_vars=task_vars,
                tmp=tmp
            )

            # Check for failure - but don't fail on expected errors
            if ndfc_result.get('failed'):
                # If the API returns an error, treat as no pairings found
                results['msg'] = f"NDFC query returned: {ndfc_result.get('msg', 'unknown error')}"
                results['ndfc_response'] = ndfc_result
                return results

            discovery_response = ndfc_result.get('response', {})
            results['ndfc_response'] = ndfc_result

        # Process the discovery response
        if not discovery_response:
            results['msg'] = 'No discovery response to process'
            return results

        processor = TorDiscoveryProcessor({'discovery_response': discovery_response})
        processor_results = processor.process()
        results.update(processor_results)

        return results

    def _run_create(self, task_vars, tmp):
        """
        Execute TOR pairing create operation.

        Returns:
            dict: Results with create operations and API results
        """
        results = {
            'failed': False,
            'operation': 'create',
            'create_operations': [],
            'api_results': [],
            'count': 0,
            'success_count': 0,
            'failure_count': 0
        }

        tor_pairing = self._task.args.get('tor_pairing', [])
        fabric_name = self._task.args.get('fabric_name', '')
        execute_api = self._task.args.get('execute_api', False)

        if not fabric_name:
            results['failed'] = True
            results['msg'] = 'Missing required parameter: fabric_name'
            return results

        if not tor_pairing:
            results['msg'] = 'No TOR pairings to create'
            return results

        # Build operations
        processor = TorCreateProcessor({
            'tor_pairing': tor_pairing,
            'fabric_name': fabric_name
        })
        create_operations = processor.build_operations()
        results['create_operations'] = create_operations
        results['count'] = len(create_operations)

        if not execute_api:
            results['msg'] = f'Prepared {len(create_operations)} TOR pairing create operation(s)'
            return results

        # Execute API calls
        display.v(f"TOR Create: Executing {len(create_operations)} POST operations")

        for op in create_operations:
            pairing_id = op['pairing_id']
            api_path = op['path']
            payload = op['payload']

            display.v(f"TOR Create: Creating pairing {pairing_id}")

            api_result = self._execute_ndfc_rest(
                method="POST",
                path=api_path,
                json_data=json.dumps(payload),
                task_vars=task_vars,
                tmp=tmp
            )

            # Capture MODULE FAILURE details from stdout/stderr
            error_msg = api_result.get('msg', '')
            if api_result.get('failed') and 'MODULE FAILURE' in error_msg:
                stdout = api_result.get('module_stdout', api_result.get('stdout', ''))
                stderr = api_result.get('module_stderr', api_result.get('stderr', ''))
                error_msg = f"{error_msg} | stdout: {stdout} | stderr: {stderr}"
                display.warning(f"TOR Create MODULE FAILURE details: {api_result}")

            op_result = {
                'pairing_id': pairing_id,
                'path': api_path,
                'success': not api_result.get('failed', False),
                'response': api_result.get('response'),
                'msg': error_msg,
                'raw_result': api_result  # Include full result for debugging
            }

            results['api_results'].append(op_result)

            if op_result['success']:
                results['success_count'] += 1
            else:
                results['failure_count'] += 1
                display.warning(f"TOR Create: Failed to create pairing {pairing_id}: {op_result['msg']}")

        # Set overall status
        if results['failure_count'] > 0 and results['success_count'] == 0:
            results['failed'] = True
            results['msg'] = f"All {results['failure_count']} TOR pairing create(s) failed"
        elif results['failure_count'] > 0:
            results['msg'] = (
                f"Created {results['success_count']} TOR pairing(s), "
                f"{results['failure_count']} failed"
            )
        else:
            results['msg'] = f"Successfully created {results['success_count']} TOR pairing(s)"

        return results

    def _run_remove(self, task_vars, tmp):
        """
        Execute TOR pairing removal operation.

        Returns:
            dict: Results with removal operations and API results
        """
        results = {
            'failed': False,
            'operation': 'remove',
            'removal_operations': [],
            'api_results': [],
            'count': 0,
            'success_count': 0,
            'failure_count': 0
        }

        tor_pairing_removed = self._task.args.get('tor_pairing_removed', [])
        fabric_name = self._task.args.get('fabric_name', '')
        execute_api = self._task.args.get('execute_api', False)

        if not fabric_name:
            results['failed'] = True
            results['msg'] = 'Missing required parameter: fabric_name'
            return results

        if not tor_pairing_removed:
            results['msg'] = 'No TOR pairings to remove'
            return results

        # Build operations
        processor = TorRemovalProcessor({
            'tor_pairing_removed': tor_pairing_removed,
            'fabric_name': fabric_name
        })
        removal_operations = processor.build_operations()
        results['removal_operations'] = removal_operations
        results['count'] = len(removal_operations)

        if not execute_api:
            results['msg'] = f'Prepared {len(removal_operations)} TOR pairing removal operation(s)'
            return results

        # Execute API calls
        display.v(f"TOR Remove: Executing {len(removal_operations)} DELETE operations")

        for op in removal_operations:
            pairing_id = op['pairing_id']
            api_path = op['path']

            display.v(f"TOR Remove: Removing pairing {pairing_id}")

            api_result = self._execute_ndfc_rest(
                method="DELETE",
                path=api_path,
                task_vars=task_vars,
                tmp=tmp
            )

            # Check for acceptable "not found" errors
            is_not_found_error = False
            error_msg = (api_result.get('msg') or '').lower()
            if 'not found' in error_msg or 'does not exist' in error_msg:
                is_not_found_error = True

            # Capture MODULE FAILURE details from stdout/stderr
            full_error_msg = api_result.get('msg', '')
            if api_result.get('failed') and 'MODULE FAILURE' in full_error_msg.upper():
                stdout = api_result.get('module_stdout', api_result.get('stdout', ''))
                stderr = api_result.get('module_stderr', api_result.get('stderr', ''))
                full_error_msg = f"{full_error_msg} | stdout: {stdout} | stderr: {stderr}"
                display.warning(f"TOR Remove MODULE FAILURE details: {api_result}")

            op_result = {
                'pairing_id': pairing_id,
                'path': api_path,
                'success': not api_result.get('failed', False) or is_not_found_error,
                'response': api_result.get('response'),
                'msg': full_error_msg,
                'already_removed': is_not_found_error,
                'raw_result': api_result  # Include full result for debugging
            }

            results['api_results'].append(op_result)

            if op_result['success']:
                results['success_count'] += 1
                if is_not_found_error:
                    display.v(f"TOR Remove: Pairing {pairing_id} already removed or not found")
            else:
                results['failure_count'] += 1
                display.warning(f"TOR Remove: Failed to remove pairing {pairing_id}: {op_result['msg']}")

        # Set overall status
        if results['failure_count'] > 0 and results['success_count'] == 0:
            results['failed'] = True
            results['msg'] = f"All {results['failure_count']} TOR pairing removal(s) failed"
        elif results['failure_count'] > 0:
            results['msg'] = (
                f"Removed {results['success_count']} TOR pairing(s), "
                f"{results['failure_count']} failed"
            )
        else:
            results['msg'] = f"Successfully removed {results['success_count']} TOR pairing(s)"

        return results

    def run(self, tmp=None, task_vars=None):
        """
        Execute the action plugin.

        Detects the operation type and delegates to the appropriate handler.

        Returns:
            dict: Results from the operation
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
                "(discovery_response, leaf_serial_number, tor_pairing, tor_pairing_removed) are set."
            )
            return results

        # Execute the appropriate operation
        try:
            if operation == 'discovery':
                return self._run_discovery(task_vars, tmp)
            elif operation == 'create':
                return self._run_create(task_vars, tmp)
            elif operation == 'remove':
                return self._run_remove(task_vars, tmp)
        except Exception as e:
            results['failed'] = True
            results['msg'] = f'Failed to execute TOR {operation}: {str(e)}'
            results['operation'] = operation
            return results

        return results

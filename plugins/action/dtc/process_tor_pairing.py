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
# TOR Diff Processor
# =============================================================================

class TorDiffProcessor:
    """
    Compare current and previous ToR pairings to identify additions and removals.

    Uses order-independent serial number matching to correctly identify
    pairings that should be removed (exist in previous but not in current).
    """

    def __init__(self, params):
        """
        Initialize the TOR diff processor.

        Args:
            params: Dictionary containing:
                - current_pairings: List of current ToR pairing dicts
                - previous_pairings: List of previous ToR pairing dicts
        """
        self.current_pairings = params.get('current_pairings', [])
        self.previous_pairings = params.get('previous_pairings', [])

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

    def compute_diff(self):
        """
        Compare current and previous ToR pairings to identify changes.

        Returns:
            dict with keys:
                - removed: list of pairings to remove (in previous but not current)
                - added: list of pairings to add (in current but not previous)
                - unchanged: list of pairings that exist in both
                - stats: dict with counts and IDs for debugging
        """
        if not self.previous_pairings:
            return {
                'removed': [],
                'added': self.current_pairings,
                'unchanged': [],
                'stats': {
                    'previous_count': 0,
                    'current_count': len(self.current_pairings),
                    'removed_count': 0,
                    'added_count': len(self.current_pairings),
                    'unchanged_count': 0
                }
            }

        # Build lookup of current pairing serials
        current_serial_map = {}
        for pairing in self.current_pairings:
            serial_key = self._normalize_serials(pairing.get('payload', {}))
            current_serial_map[serial_key] = pairing

        # Build lookup of previous pairing serials
        previous_serial_map = {}
        for pairing in self.previous_pairings:
            serial_key = self._normalize_serials(pairing.get('payload', {}))
            previous_serial_map[serial_key] = pairing

        # Find removals (in previous but not in current)
        removed = []
        unchanged_from_previous = []
        for serial_key, prev_pairing in previous_serial_map.items():
            if serial_key not in current_serial_map:
                removed.append(prev_pairing)
            else:
                unchanged_from_previous.append(prev_pairing)

        # Find additions (in current but not in previous)
        added = []
        for serial_key, curr_pairing in current_serial_map.items():
            if serial_key not in previous_serial_map:
                added.append(curr_pairing)

        # Return results with statistics for debugging
        return {
            'removed': removed,
            'added': added,
            'unchanged': unchanged_from_previous,
            'stats': {
                'previous_count': len(self.previous_pairings),
                'current_count': len(self.current_pairings),
                'removed_count': len(removed),
                'added_count': len(added),
                'unchanged_count': len(unchanged_from_previous),
                'previous_ids': [p.get('pairing_id', 'unknown') for p in self.previous_pairings],
                'current_ids': [p.get('pairing_id', 'unknown') for p in self.current_pairings],
                'removed_ids': [p.get('pairing_id', 'unknown') for p in removed],
                'added_ids': [p.get('pairing_id', 'unknown') for p in added]
            }
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

        # Step 5: Convert to JSON (compact format, no spaces) and URL encode
        # NDFC expects compact JSON: {"leafSN1":"torSN1,torSN2","leafSN2":"torSN1,torSN2"}
        leaftor_json = json.dumps(leaftor_map, separators=(',', ':'))
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
# Action Module
# =============================================================================

class ActionModule(ActionBase):
    """
    Ansible action plugin for TOR pairing create/remove operations.

    Two operations, each with two modes:

    **Direct mode** — pre-computed items passed via ``pairings``:

        - name: Create TOR pairings (diff run active)
          cisco.nac_dc_vxlan.dtc.process_tor_pairing:
            operation: create
            pairings: "{{ diff_items }}"
            fabric_name: "{{ fabric }}"

        - name: Remove TOR pairings (diff run active)
          cisco.nac_dc_vxlan.dtc.process_tor_pairing:
            operation: remove
            pairings: "{{ diff_items }}"
            fabric_name: "{{ fabric }}"

    **Discovery mode** — discover from NDFC, diff, then execute:

        - name: Create TOR pairings (diff run disabled)
          cisco.nac_dc_vxlan.dtc.process_tor_pairing:
            operation: create
            fabric_name: "{{ fabric }}"
            leaf_serial_number: "{{ leaf_sn }}"
            current_pairings: "{{ desired_pairings }}"

        - name: Remove TOR pairings (diff run disabled)
          cisco.nac_dc_vxlan.dtc.process_tor_pairing:
            operation: remove
            fabric_name: "{{ fabric }}"
            leaf_serial_number: "{{ leaf_sn }}"
            current_pairings: "{{ desired_pairings }}"

    Parameters:
        operation (str):          Required. 'create' or 'remove'.
        fabric_name (str):        Required. Target NDFC fabric name.
        pairings (list):          Direct mode — pre-computed pairing dicts.
        leaf_serial_number (str): Discovery mode — triggers NDFC query + diff.
        current_pairings (list):  Discovery mode — desired state to diff against.
    """

    # ─── NDFC REST helper ─────────────────────────────────────────────

    def _execute_ndfc_rest(
        self, method, path, json_data=None, task_vars=None, tmp=None
    ):
        """Execute an NDFC REST API call via cisco.dcnm.dcnm_rest."""
        module_args = {"method": method, "path": path}
        if json_data is not None:
            module_args["data"] = json_data
        return self._execute_module(
            module_name="cisco.dcnm.dcnm_rest",
            module_args=module_args,
            task_vars=task_vars,
            tmp=tmp,
        )

    # ─── Discovery ────────────────────────────────────────────────────

    def _discover_pairings(self, fabric_name, leaf_serial_number, task_vars, tmp):
        """
        Query NDFC for existing TOR pairings and parse the response.

        Returns:
            dict with 'discovered_pairings' list and 'failed' status.
        """
        api_path = (
            f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/tor/"
            f"fabrics/{fabric_name}/switches/{leaf_serial_number}"
        )
        display.v(f"TOR Discovery: Querying NDFC at {api_path}")

        ndfc_result = self._execute_ndfc_rest(
            method="GET", path=api_path, task_vars=task_vars, tmp=tmp
        )

        if ndfc_result.get('failed'):
            return {
                'failed': False,
                'discovered_pairings': [],
                'msg': f"NDFC query returned: {ndfc_result.get('msg', 'unknown error')}",
            }

        discovery_response = ndfc_result.get('response', {})
        if not discovery_response:
            return {
                'failed': False,
                'discovered_pairings': [],
                'msg': 'No discovery response to process',
            }

        processor = TorDiscoveryProcessor({'discovery_response': discovery_response})
        result = processor.process()
        return {'failed': False, **result}

    # ─── Execution helpers ────────────────────────────────────────────

    def _execute_create_operations(self, pairings, fabric_name, task_vars, tmp):
        """Build and execute TOR pairing create operations via NDFC POST."""
        result = {
            'failed': False,
            'api_results': [],
            'count': 0,
            'success_count': 0,
            'failure_count': 0,
        }

        processor = TorCreateProcessor({
            'tor_pairing': pairings,
            'fabric_name': fabric_name,
        })
        operations = processor.build_operations()
        result['count'] = len(operations)

        if not operations:
            result['msg'] = 'No valid TOR pairing create operations to execute'
            return result

        display.v(f"TOR Create: Executing {len(operations)} POST operations")

        for op in operations:
            pairing_id = op['pairing_id']
            display.v(f"TOR Create: Creating pairing {pairing_id}")

            api_result = self._execute_ndfc_rest(
                method="POST",
                path=op['path'],
                json_data=json.dumps(op['payload']),
                task_vars=task_vars,
                tmp=tmp,
            )

            raw_msg = api_result.get('msg', '')
            if isinstance(raw_msg, dict):
                error_msg = json.dumps(raw_msg)
            else:
                error_msg = str(raw_msg) if raw_msg else ''

            if api_result.get('failed') and 'MODULE FAILURE' in str(error_msg).upper():
                stdout = api_result.get('module_stdout', api_result.get('stdout', ''))
                stderr = api_result.get('module_stderr', api_result.get('stderr', ''))
                error_msg = f"{error_msg} | stdout: {stdout} | stderr: {stderr}"
                display.warning(f"TOR Create MODULE FAILURE details: {api_result}")

            op_result = {
                'pairing_id': pairing_id,
                'path': op['path'],
                'success': not api_result.get('failed', False),
                'response': api_result.get('response'),
                'msg': error_msg,
                'raw_result': api_result,
            }
            result['api_results'].append(op_result)

            if op_result['success']:
                result['success_count'] += 1
            else:
                result['failure_count'] += 1
                display.warning(
                    f"TOR Create: Failed to create pairing {pairing_id}: {op_result['msg']}"
                )

        if result['failure_count'] > 0 and result['success_count'] == 0:
            result['failed'] = True
            result['msg'] = f"All {result['failure_count']} TOR pairing create(s) failed"
        elif result['failure_count'] > 0:
            result['msg'] = (
                f"Created {result['success_count']} TOR pairing(s), "
                f"{result['failure_count']} failed"
            )
        else:
            result['msg'] = f"Successfully created {result['success_count']} TOR pairing(s)"

        return result

    def _execute_remove_operations(self, pairings, fabric_name, task_vars, tmp):
        """Build and execute TOR pairing remove operations via NDFC DELETE."""
        result = {
            'failed': False,
            'api_results': [],
            'count': 0,
            'success_count': 0,
            'failure_count': 0,
        }

        processor = TorRemovalProcessor(
            {"tor_pairing_removed": pairings, "fabric_name": fabric_name}
        )
        operations = processor.build_operations()
        result['count'] = len(operations)

        if not operations:
            result['msg'] = 'No valid TOR pairing removal operations to execute'
            return result

        display.v(f"TOR Remove: Executing {len(operations)} DELETE operations")

        for op in operations:
            pairing_id = op['pairing_id']
            display.v(f"TOR Remove: Removing pairing {pairing_id}")

            api_result = self._execute_ndfc_rest(
                method="DELETE",
                path=op['path'],
                task_vars=task_vars,
                tmp=tmp,
            )

            raw_msg = api_result.get('msg', '')
            if isinstance(raw_msg, dict):
                error_msg_str = (
                    str(raw_msg.get('DATA', '')) + ' ' + str(raw_msg.get('MESSAGE', ''))
                )
                full_error_msg = json.dumps(raw_msg)
            else:
                error_msg_str = str(raw_msg) if raw_msg else ''
                full_error_msg = error_msg_str

            is_not_found_error = False
            error_msg_lower = error_msg_str.lower()
            if 'not found' in error_msg_lower or 'does not exist' in error_msg_lower:
                is_not_found_error = True

            if api_result.get('failed') and 'MODULE FAILURE' in full_error_msg.upper():
                stdout = api_result.get('module_stdout', api_result.get('stdout', ''))
                stderr = api_result.get('module_stderr', api_result.get('stderr', ''))
                full_error_msg = f"{full_error_msg} | stdout: {stdout} | stderr: {stderr}"
                display.warning(f"TOR Remove MODULE FAILURE details: {api_result}")

            op_result = {
                'pairing_id': pairing_id,
                'path': op['path'],
                'success': not api_result.get('failed', False) or is_not_found_error,
                'response': api_result.get('response'),
                'msg': full_error_msg,
                'already_removed': is_not_found_error,
                'raw_result': api_result,
            }
            result['api_results'].append(op_result)

            if op_result['success']:
                result['success_count'] += 1
                if is_not_found_error:
                    display.v(
                        f"TOR Remove: Pairing {pairing_id} already removed or not found"
                    )
            else:
                result['failure_count'] += 1
                display.warning(
                    f"TOR Remove: Failed to remove pairing {pairing_id}: {op_result['msg']}"
                )

        if result['failure_count'] > 0 and result['success_count'] == 0:
            result['failed'] = True
            result['msg'] = f"All {result['failure_count']} TOR pairing removal(s) failed"
        elif result['failure_count'] > 0:
            result['msg'] = (
                f"Removed {result['success_count']} TOR pairing(s), "
                f"{result['failure_count']} failed"
            )
        else:
            result['msg'] = f"Successfully removed {result['success_count']} TOR pairing(s)"

        return result

    # ─── Mode dispatch ────────────────────────────────────────────────

    def _execute_direct(self, operation, pairings, fabric_name, task_vars, tmp):
        """Direct mode: execute on pre-computed pairing items."""
        display.v(
            f"TOR {operation.title()}: Direct mode — "
            f"{len(pairings)} pairing(s) to {operation}"
        )
        if operation == 'create':
            result = self._execute_create_operations(
                pairings, fabric_name, task_vars, tmp
            )
        else:
            result = self._execute_remove_operations(
                pairings, fabric_name, task_vars, tmp
            )
        result['operation'] = operation
        return result

    def _execute_with_discovery(self, operation, fabric_name, task_vars, tmp):
        """Discovery mode: query NDFC, diff against desired state, then execute."""
        leaf_serial_number = self._task.args.get('leaf_serial_number', '')
        current_pairings = self._task.args.get('current_pairings', []) or []

        # Step 1: Discover existing pairings from NDFC
        discovery = self._discover_pairings(
            fabric_name, leaf_serial_number, task_vars, tmp
        )
        if discovery.get('failed'):
            discovery['operation'] = operation
            return discovery

        discovered = discovery.get('discovered_pairings', [])

        # Step 2: Diff discovered (NDFC state) against desired (current_pairings)
        diff = TorDiffProcessor({
            'current_pairings': current_pairings,
            'previous_pairings': discovered,
        }).compute_diff()

        # Pick the relevant diff key for this operation
        items = diff.get('added', []) if operation == 'create' else diff.get('removed', [])

        display.v(
            f"TOR {operation.title()}: Discovery mode — "
            f"{len(discovered)} discovered, {len(items)} to {operation}"
        )

        if not items:
            return {
                'failed': False,
                'operation': operation,
                'discovered_count': len(discovered),
                'diff_stats': diff.get('stats', {}),
                'msg': f"No TOR pairings to {operation} after discovery diff",
            }

        # Step 3: Execute
        if operation == 'create':
            result = self._execute_create_operations(
                items, fabric_name, task_vars, tmp
            )
        else:
            result = self._execute_remove_operations(
                items, fabric_name, task_vars, tmp
            )

        result['operation'] = operation
        result['discovered_count'] = len(discovered)
        result['diff_stats'] = diff.get('stats', {})
        return result

    # ─── Entry point ──────────────────────────────────────────────────

    def run(self, tmp=None, task_vars=None):
        """
        Execute the action plugin.

        Routes to direct mode (pairings provided) or discovery mode
        (leaf_serial_number provided) based on parameters.
        """
        results = super(ActionModule, self).run(tmp, task_vars)

        operation = self._task.args.get('operation')
        fabric_name = self._task.args.get('fabric_name', '')
        pairings = self._task.args.get('pairings', [])
        leaf_serial_number = self._task.args.get('leaf_serial_number', '')

        if operation not in ('create', 'remove'):
            results['failed'] = True
            results['msg'] = (
                "operation must be 'create' or 'remove', "
                f"got: {operation!r}"
            )
            return results

        if not fabric_name:
            results['failed'] = True
            results['msg'] = 'Missing required parameter: fabric_name'
            return results

        try:
            # Direct mode: pre-computed items
            if pairings:
                return self._execute_direct(
                    operation, pairings, fabric_name, task_vars, tmp
                )

            # Discovery mode: query NDFC, diff, execute
            if leaf_serial_number:
                return self._execute_with_discovery(
                    operation, fabric_name, task_vars, tmp
                )

            # Nothing to do
            results['operation'] = operation
            results['msg'] = (
                f'No pairings or leaf_serial_number provided — skipped'
            )
            return results

        except Exception as e:
            results['failed'] = True
            results['msg'] = f'Failed to execute TOR {operation}: {str(e)}'
            results['operation'] = operation
            return results

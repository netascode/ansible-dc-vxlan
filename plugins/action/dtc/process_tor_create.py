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

    def process_creates(self):
        """
        Process all TOR pairings to be created and build create operations.

        Returns:
            list: List of create operation dictionaries, each containing:
                - pairing_id: Identifier for the pairing
                - path: NDFC API POST path
                - json_data: JSON payload for the API call
                - payload: Original payload (for reference)
                - scenario: Pairing scenario type
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

        return self.create_operations


class ActionModule(ActionBase):
    """
    Ansible action plugin to process TOR pairing creates.

    This plugin takes a list of TOR pairings to be created and validates
    them, preparing the necessary NDFC API POST operations.

    Usage:
        - name: Process TOR create operations
          cisco.nac_dc_vxlan.dtc.process_tor_create:
            tor_pairing: "{{ vars_common_local.tor_pairing }}"
            fabric_name: "{{ MD_Extended.vxlan.fabric.name }}"
          register: tor_create_operations
    """

    def run(self, tmp=None, task_vars=None):
        """
        Execute the action plugin.

        Returns:
            dict: Results containing:
                - create_operations: List of create operation dicts
                - count: Number of create operations
                - msg: Status message
        """
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False

        # Get parameters from task
        params = {
            'tor_pairing': self._task.args.get('tor_pairing', []),
            'fabric_name': self._task.args.get('fabric_name', '')
        }

        # Validate required parameters
        if not params['fabric_name']:
            results['failed'] = True
            results['msg'] = 'Missing required parameter: fabric_name'
            return results

        if not params['tor_pairing']:
            results['create_operations'] = []
            results['count'] = 0
            results['msg'] = 'No TOR pairings to create'
            return results

        # Initialize processor
        processor = TorCreateProcessor(params)

        # Process creates
        try:
            create_operations = processor.process_creates()

            results['create_operations'] = create_operations
            results['count'] = len(create_operations)
            results['msg'] = f'Prepared {len(create_operations)} TOR pairing create operation(s)'

        except Exception as e:
            results['failed'] = True
            results['msg'] = f'Failed to process TOR creates: {str(e)}'
            results['create_operations'] = []
            results['count'] = 0

        return results

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

from ansible.utils.display import Display
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import data_model_key_check

display = Display()

PARENT_KEYS = ['vxlan', 'global']

# Deprecated global keys that are still supported for backwards compatibility
BACKWARD_COMPATIBLE_KEYS = [
    "bgp_asn",
    "route_reflectors",
    "anycast_gateway_mac",
    "layer2_vni_range",
    "layer3_vni_range",
    "layer2_vlan_range",
    "layer3_vlan_range",
    "vpc",
    "ptp",
    "snmp_server_host_trap",
    "enable_nxapi_http",
    "nxapi_http_port",
    "enable_nxapi_https",
    "nxapi_https_port",
    "spanning_tree",
    "auth_proto",
    "dns_servers",
    "ntp_servers",
    "syslog_servers",
    "netflow",
    "bootstrap"
]


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        model_data = self.kwargs['results']['model_extended']

        new_global_key = None
        if model_data['vxlan']['fabric']['type'] == 'VXLAN_EVPN':
            new_global_key = 'ibgp'
            PARENT_KEYS.append(new_global_key)
        elif model_data['vxlan']['fabric']['type'] == 'External':
            new_global_key = 'external'
            PARENT_KEYS.append(new_global_key)

        if new_global_key:
            dm_check = data_model_key_check(model_data, PARENT_KEYS)

            # This if handles the case where the new global key does not exist at all
            # or exists but has no data. This is to ensure that the new global key is
            # created and populated with the data from the old global key if it exists.
            # If the new global key already exists and has data, it will not be overwritten.
            if new_global_key in dm_check['keys_not_found'] or new_global_key in dm_check['keys_no_data']:
                deprecated_msg = (
                    f"Attempting to use vxlan.global keys due to vxlan.fabric.global.{new_global_key} not being defined. "
                    f"General vxlan.global keys are being deprecated. Please use vxlan.fabric.global.{new_global_key}."
                )
                display.deprecated(msg=deprecated_msg, version="1.0.0", collection_name='cisco.nac_dc_vxlan')

                model_data['vxlan']['global'].update({new_global_key: {}})

                for key in BACKWARD_COMPATIBLE_KEYS:
                    if key in model_data['vxlan']['global']:
                        model_data['vxlan']['fabric']['ibgp'].update({key: model_data['vxlan']['global'][key]})

            # This elif handles the case where the new global key exists but is empty or has data while data still exists
            # under the old global key. This is to ensure that the new global key is populated with the data from the old
            # global key if it exists and only if the new global key does not already have data at the key location.
            elif new_global_key in dm_check['keys_found'] and (new_global_key in dm_check['keys_data'] or new_global_key in dm_check['keys_no_data']):
                for key in BACKWARD_COMPATIBLE_KEYS:
                    # Check if the key exists in the new global key
                    dm_check = data_model_key_check(model_data, PARENT_KEYS + [key])
                    # If the key does not exist or has no data in the new global key, we can safely try to copy the data
                    # from the old global key to the new global key if the old global key has data
                    if key in dm_check['keys_not_found'] or key in dm_check['keys_no_data']:
                        # Check if the key exists in the old global key
                        dm_check = data_model_key_check(model_data, PARENT_KEYS[:-1])
                        # If the key exists and has data in the old global key, we can copy the data
                        if key in dm_check['keys_found'] and key in dm_check['keys_data']:
                            model_data['vxlan']['fabric']['global']['ibgp'].update({key: model_data['vxlan']['global'][key]})

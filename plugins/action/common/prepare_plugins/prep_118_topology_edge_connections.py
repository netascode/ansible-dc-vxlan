# Copyright (c) 2024 Cisco Systems, Inc. and its affiliates
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

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import normalize_interface_name


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        data_model = self.kwargs['results']['model_extended']

        # This plugin does not apply to the follwing fabric types
        if data_model['vxlan']['fabric']['type'] in ['MSD', 'MCFG']:
            return self.kwargs['results']
        else:
            switches = data_model['vxlan']['topology']['switches']

        # Ensure that edge_connection's switches are mapping to their respective
        # management IP address from topology switches
        topology_switches = data_model['vxlan']['topology']['switches']
        for link in data_model['vxlan']['topology']['edge_connections']:
            if any(sw['name'] == link['source_device'] for sw in topology_switches):
                found_switch = next((item for item in topology_switches if item["name"] == link['source_device']))
                if found_switch.get('management').get('management_ipv4_address'):
                    link['source_device_ip'] = found_switch['management']['management_ipv4_address']
                elif found_switch.get('management').get('management_ipv6_address'):
                    link['source_device_ip'] = found_switch['management']['management_ipv6_address']

                # For eBGP_VXLAN, we need to get the leaf overlay interface IP list and ASNs from the policy template variables to get the ASN number
                if data_model['vxlan']['fabric']['type'] == 'eBGP_VXLAN':
                    policies = data_model['vxlan']['policy']['policies']
                    # ebgp_overlay_spine_all_neighbor_custom template has the list of leaf IPs and ASNs configured as neighbors on the spines
                    spine_neighbor_policy = next(
                        (item for item in policies if item['template_name'] == 'ebgp_overlay_spine_all_neighbor_custom'), None
                    )
                    leaf_ip_list = spine_neighbor_policy['template_vars']['LEAF_IP_LIST'].split(',')
                    leaf_asns = spine_neighbor_policy['template_vars']['LEAF_ASNS'].split(',')

                    # ebgp_overlay_leaf_all_neighbor_custom template has the leaf overlay source interface name
                    # for the neighborship with the spines
                    leaf_neighbor_policy = next(
                        (item for item in policies if item['template_name'] == 'ebgp_overlay_leaf_all_neighbor_custom'), None
                    )
                    leaf_overlay_int = normalize_interface_name(leaf_neighbor_policy['template_vars']['INTF_NAME'])

                    leaf_overlay_int_ip = next(
                        item for item in found_switch['interfaces']
                        if normalize_interface_name(item['name']) == leaf_overlay_int
                    )['ipv4_address']
                    sw_index = [index for index in range(len(leaf_ip_list)) if leaf_ip_list[index] == leaf_overlay_int_ip][0]
                    bgp_asn = leaf_asns[sw_index]
                    link['source_device_bgp_asn'] = bgp_asn

        self.kwargs['results']['model_extended'] = data_model
        return self.kwargs['results']

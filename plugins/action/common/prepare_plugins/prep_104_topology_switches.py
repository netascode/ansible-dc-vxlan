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

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import hostname_to_ip_mapping, data_model_key_check


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        data_model = self.kwargs['results']['model_extended']

        # This plugin does not apply to the follwing fabric types
        if data_model['vxlan']['fabric']['type'] in ['MSD', 'MFD']:
            return self.kwargs['results']
        else:
            switches = data_model['vxlan']['topology']['switches']

        #  Loop over all the roles in vxlan.topology.switches.role
        data_model['vxlan']['topology']['spine'] = {}
        data_model['vxlan']['topology']['leaf'] = {}
        data_model['vxlan']['topology']['border'] = {}
        data_model['vxlan']['topology']['border_spine'] = {}
        data_model['vxlan']['topology']['border_gateway'] = {}
        data_model['vxlan']['topology']['border_gateway_spine'] = {}
        data_model['vxlan']['topology']['super_spine'] = {}
        data_model['vxlan']['topology']['border_super_spine'] = {}
        data_model['vxlan']['topology']['border_gateway_super_spine'] = {}
        data_model['vxlan']['topology']['tor'] = {}
        data_model['vxlan']['topology']['core_router'] = {}
        data_model['vxlan']['topology']['edge_router'] = {}
        sm_switches = data_model['vxlan']['topology']['switches']
        for switch in sm_switches:
            # Build list of switch IP's based on role keyed by switch name
            name = switch.get('name')
            role = switch.get('role')
            data_model['vxlan']['topology'][role][name] = {}
            v4_key = 'management_ipv4_address'
            v6_key = 'management_ipv6_address'
            v4ip = switch.get('management').get(v4_key)
            v6ip = switch.get('management').get(v6_key)
            data_model['vxlan']['topology'][role][name][v4_key] = v4ip
            data_model['vxlan']['topology'][role][name][v6_key] = v6ip

        data_model = hostname_to_ip_mapping(data_model)

        # Check for vpc_peers in the data model
        # If found, update the data model with the management IP address of the peer switches
        # for templating later.
        vpc_peers_keys = ['vxlan', 'topology', 'vpc_peers']
        dm_check = data_model_key_check(data_model, vpc_peers_keys)
        if 'vpc_peers' in dm_check['keys_found'] and 'vpc_peers' in dm_check['keys_data']:
            vpc_peers_pairs = data_model['vxlan']['topology']['vpc_peers']

            # Before:
            # 'vpc_peers': [
            #     {
            #         'domain_id': 1,
            #         'fabric_peering': True,
            #         'peer1': 'nac-leaf1',
            #         'peer2': 'nac-leaf2',
            #     },
            #     {
            #         'fabric_peering': False,
            #         'peer1': 'nac-leaf3',
            #         'peer1_peerlink_interfaces': [
            #             {
            #                 'name': 'Ethernet1/4'
            #             },
            #             {
            #                 'name': 'Ethernet1/5'
            #             }
            #         ],
            #         'peer2': 'nac-leaf4',
            #         'peer2_peerlink_interfaces': [
            #             {
            #                 'name': 'Ethernet1/4'
            #             },
            #             {
            #                 'name': 'Ethernet1/5'
            #             }
            #         ]
            #     }
            # ]
            # After:
            # 'vpc_peers': [
            #     {
            #         'domain_id': 1,
            #         'fabric_peering': True,
            #         'peer1': 'nac-leaf1',
            #         'peer1_mgmt_ip_address': '10.15.33.13',
            #         'peer2': 'nac-leaf2',
            #         'peer2_mgmt_ip_address': '10.15.33.14'
            #     },
            #     {
            #         'fabric_peering': False,
            #         'peer1': 'nac-leaf3',
            #         'peer1_mgmt_ip_address': '10.15.33.15',
            #         'peer1_peerlink_interfaces': [
            #             {
            #                 'name': 'Ethernet1/4'
            #             },
            #             {
            #                 'name': 'Ethernet1/5'
            #             }
            #         ],
            #         'peer2': 'nac-leaf4',
            #         'peer2_mgmt_ip_address': '10.15.33.16',
            #         'peer2_peerlink_interfaces': [
            #             {
            #                 'name': 'Ethernet1/4'
            #             },
            #             {
            #                 'name': 'Ethernet1/5'
            #             }
            #         ]
            #     }
            # ]
            for vpc_peers_pair in vpc_peers_pairs:
                if any(sw['name'] == vpc_peers_pair['peer1'] for sw in switches):
                    found_switch = next((item for item in switches if item["name"] == vpc_peers_pair['peer1']))
                    if found_switch.get('management').get('management_ipv4_address'):
                        vpc_peers_pair['peer1_mgmt_ip_address'] = found_switch['management']['management_ipv4_address']
                    elif found_switch.get('management').get('management_ipv6_address'):
                        vpc_peers_pair['peer1_mgmt_ip_address'] = found_switch['management']['management_ipv6_address']
                if any(sw['name'] == vpc_peers_pair['peer2'] for sw in switches):
                    found_switch = next((item for item in switches if item["name"] == vpc_peers_pair['peer2']))
                    if found_switch.get('management').get('management_ipv4_address'):
                        vpc_peers_pair['peer2_mgmt_ip_address'] = found_switch['management']['management_ipv4_address']
                    elif found_switch.get('management').get('management_ipv6_address'):
                        vpc_peers_pair['peer2_mgmt_ip_address'] = found_switch['management']['management_ipv6_address']

        # Check for fabric_links in the data model
        # If found, update the data model with the management IP address of the switches for templating later.
        fabric_links_keys = ['vxlan', 'topology', 'fabric_links']
        dm_check = data_model_key_check(data_model, fabric_links_keys)
        if 'fabric_links' in dm_check['keys_found'] and 'fabric_links' in dm_check['keys_data']:
            fabric_links = data_model['vxlan']['topology']['fabric_links']

            # Similar before and after transformation as above with vpc_peers
            # source_device_mgmt_ip_address and dest_device_mgmt_ip_address are added to the fabric_links part of the model
            for fabric_link in fabric_links:
                if any(sw['name'] == fabric_link['source_device'] for sw in switches):
                    found_switch = next((item for item in switches if item["name"] == fabric_link['source_device']))
                    if found_switch.get('management').get('management_ipv4_address'):
                        fabric_link['source_device_mgmt_ip_address'] = found_switch['management']['management_ipv4_address']
                    elif found_switch.get('management').get('management_ipv6_address'):
                        fabric_link['source_device_mgmt_ip_address'] = found_switch['management']['management_ipv6_address']
                if any(sw['name'] == fabric_link['dest_device'] for sw in switches):
                    found_switch = next((item for item in switches if item["name"] == fabric_link['dest_device']))
                    if found_switch.get('management').get('management_ipv4_address'):
                        fabric_link['dest_device_mgmt_ip_address'] = found_switch['management']['management_ipv4_address']
                    elif found_switch.get('management').get('management_ipv6_address'):
                        fabric_link['dest_device_mgmt_ip_address'] = found_switch['management']['management_ipv6_address']

        self.kwargs['results']['model_extended'] = data_model

        return self.kwargs['results']

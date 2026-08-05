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

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import (
    restructure_leaf_tor_data,
    resolve_switch_by_identifier,
)


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def _resolve_mgmt_ip(self, identifier, topology_switches):
        found = resolve_switch_by_identifier(identifier, topology_switches)
        mgmt = found.get('management') or {}
        return (
            mgmt.get('management_ipv4_address')
            or mgmt.get('management_ipv6_address')
        )

    def prepare(self):
        data_model = self.kwargs['results']['model_extended']

        # We don't have switches for Multisite fabrics so need special handling
        if data_model['vxlan']['fabric']['type'] in ('MSD', 'MCFG'):
            switches = []
        else:
            switches = data_model['vxlan']['topology']['switches']

        tor_peers = data_model['vxlan'].get("topology", {}).get("tor_peers", [])

        if data_model['vxlan']['fabric']['type'] in ('VXLAN_EVPN', 'eBGP_VXLAN'):
            # Rebuild sm_data['vxlan']['overlay']['vrf_attach_groups'] into
            # a structure that is easier to use.
            vrf_grp_name_list = []
            data_model['vxlan']['overlay']['vrf_attach_groups_dict'] = {}
            for grp in data_model['vxlan']['overlay']['vrf_attach_groups']:
                data_model['vxlan']['overlay']['vrf_attach_groups_dict'][grp['name']] = []
                vrf_grp_name_list.append(grp['name'])
                for switch in grp['switches']:
                    data_model['vxlan']['overlay']['vrf_attach_groups_dict'][grp['name']].append(switch)
                for switch in data_model['vxlan']['overlay']['vrf_attach_groups_dict'][grp['name']]:
                    switch['mgmt_ip_address'] = self._resolve_mgmt_ip(switch['hostname'], switches)

            # Remove vrf_attach_group from vrf if the group_name is not defined
            for vrf in data_model['vxlan']['overlay']['vrfs']:
                if 'vrf_attach_group' in vrf:
                    if vrf.get('vrf_attach_group') not in vrf_grp_name_list:
                        del vrf['vrf_attach_group']

            # Rebuild sm_data['vxlan']['overlay']['network_attach_groups'] into
            # a structure that is easier to use.
            net_grp_name_list = []
            data_model['vxlan']['overlay']['network_attach_groups_dict'] = {}
            for grp in data_model['vxlan']['overlay']['network_attach_groups']:
                data_model['vxlan']['overlay']['network_attach_groups_dict'][grp['name']] = []
                net_grp_name_list.append(grp['name'])

                # Restructure flat TOR entries under parent leaves
                grp['switches'] = restructure_leaf_tor_data(
                    grp['switches'], switches, tor_peers
                )

                for switch in grp['switches']:
                    data_model['vxlan']['overlay']['network_attach_groups_dict'][grp['name']].append(switch)
                for switch in data_model['vxlan']['overlay']['network_attach_groups_dict'][grp['name']]:
                    switch['mgmt_ip_address'] = self._resolve_mgmt_ip(switch['hostname'], switches)

                    if 'tors' in switch and switch['tors']:
                        for tor in switch['tors']:
                            tor_id = tor.get('hostname')
                            if not tor_id:
                                continue
                            tor['mgmt_ip_address'] = self._resolve_mgmt_ip(tor_id, switches)

            # Remove network_attach_group from net if the group_name is not defined
            for net in data_model['vxlan']['overlay']['networks']:
                if 'network_attach_group' in net:
                    if net.get('network_attach_group') not in net_grp_name_list:
                        del net['network_attach_group']

            for net in data_model['vxlan']['overlay']['networks']:
                overrides = net.get('switch_attach_overrides')
                if not overrides:
                    continue
                for override in overrides:
                    override_id = override.get('hostname')
                    if not override_id:
                        continue
                    override['mgmt_ip_address'] = self._resolve_mgmt_ip(override_id, switches)

        self.kwargs['results']['model_extended'] = data_model
        return self.kwargs['results']

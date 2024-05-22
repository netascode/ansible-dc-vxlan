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


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        model_data = self.kwargs['results']['model_extended']
        switches = model_data['vxlan']['topology']['switches']

        # Rebuild sm_data['vxlan']['overlay_services']['vrf_attach_groups'] into
        # a structure that is easier to use.
        vrf_grp_name_list = []
        model_data['vxlan']['overlay_services']['vrf_attach_groups_dict'] = {}
        for grp in model_data['vxlan']['overlay_services']['vrf_attach_groups']:
            model_data['vxlan']['overlay_services']['vrf_attach_groups_dict'][grp['name']] = []
            vrf_grp_name_list.append(grp['name'])
            for switch in grp['switches']:
                model_data['vxlan']['overlay_services']['vrf_attach_groups_dict'][grp['name']].append(switch)
            # If the switch is in the switch list and a hostname is used, replace the hostname with the management IP
            for switch in model_data['vxlan']['overlay_services']['vrf_attach_groups_dict'][grp['name']]:
                if any(sw['name'] == switch['hostname'] for sw in switches):
                    found_switch = next((item for item in switches if item["name"] == switch['hostname']))
                    if found_switch.get('management').get('management_ipv4_address'):
                        switch['hostname'] = found_switch['management']['management_ipv4_address']
                    elif found_switch.get('management').get('management_ipv6_address'):
                        switch['hostname'] = found_switch['management']['management_ipv6_address']

        # Remove attach_group from vrf if the group_name is not defined
        for vrf in model_data['vxlan']['overlay_services']['vrfs']:
            if 'attach_group' in vrf:
                if vrf.get('attach_group') not in vrf_grp_name_list:
                    del vrf['attach_group']

        # Rebuild sm_data['vxlan']['overlay_services']['network_attach_groups'] into
        # a structure that is easier to use.
        net_grp_name_list = []
        model_data['vxlan']['overlay_services']['network_attach_groups_dict'] = {}
        for grp in model_data['vxlan']['overlay_services']['network_attach_groups']:
            model_data['vxlan']['overlay_services']['network_attach_groups_dict'][grp['name']] = []
            net_grp_name_list.append(grp['name'])
            for switch in grp['switches']:
                model_data['vxlan']['overlay_services']['network_attach_groups_dict'][grp['name']].append(switch)
            # If the switch is in the switch list and a hostname is used, replace the hostname with the management IP
            for switch in model_data['vxlan']['overlay_services']['network_attach_groups_dict'][grp['name']]:
                if any(sw['name'] == switch['hostname'] for sw in switches):
                    found_switch = next((item for item in switches if item["name"] == switch['hostname']))
                    if found_switch.get('management').get('management_ipv4_address'):
                        switch['hostname'] = found_switch['management']['management_ipv4_address']
                    elif found_switch.get('management').get('management_ipv6_address'):
                        switch['hostname'] = found_switch['management']['management_ipv6_address']

        # Remove attach_group from net if the group_name is not defined
        for net in model_data['vxlan']['overlay_services']['networks']:
            if 'attach_group' in net:
                if net.get('attach_group') not in net_grp_name_list:
                    del net['attach_group']

        self.kwargs['results']['model_extended'] = model_data
        return self.kwargs['results']

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
        data_model = self.kwargs['results']['model_extended']

        # We don't have switches for Multisite fabrics so need special handling
        if data_model['vxlan']['fabric']['type'] in ('MSD', 'MCFG'):
            switches = []
        else:
            switches = data_model['vxlan']['topology']['switches']

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
                # If the switch is in the switch list and a hostname is used, replace the hostname with the management IP
                for switch in data_model['vxlan']['overlay']['vrf_attach_groups_dict'][grp['name']]:
                    if any(sw['name'] == switch['hostname'] for sw in switches):
                        found_switch = next((item for item in switches if item["name"] == switch['hostname']))
                        if found_switch.get('management').get('management_ipv4_address'):
                            switch['mgmt_ip_address'] = found_switch['management']['management_ipv4_address']
                        elif found_switch.get('management').get('management_ipv6_address'):
                            switch['mgmt_ip_address'] = found_switch['management']['management_ipv6_address']

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
                for switch in grp['switches']:
                    data_model['vxlan']['overlay']['network_attach_groups_dict'][grp['name']].append(switch)
                # If the switch is in the switch list and a hostname is used, replace the hostname with the management IP
                for switch in data_model['vxlan']['overlay']['network_attach_groups_dict'][grp['name']]:
                    if any(sw['name'] == switch['hostname'] for sw in switches):
                        found_switch = next((item for item in switches if item["name"] == switch['hostname']))
                        if found_switch.get('management').get('management_ipv4_address'):
                            switch['mgmt_ip_address'] = found_switch['management']['management_ipv4_address']
                        elif found_switch.get('management').get('management_ipv6_address'):
                            switch['mgmt_ip_address'] = found_switch['management']['management_ipv6_address']

                    # Process nested TOR entries and resolve their management IPs
                    if 'tors' in switch and switch['tors']:
                        for tor in switch['tors']:
                            tor_hostname = tor.get('hostname')
                            if tor_hostname and any(sw['name'] == tor_hostname for sw in switches):
                                found_tor = next((item for item in switches if item["name"] == tor_hostname))
                                if found_tor.get('management').get('management_ipv4_address'):
                                    tor['mgmt_ip_address'] = found_tor['management']['management_ipv4_address']
                                elif found_tor.get('management').get('management_ipv6_address'):
                                    tor['mgmt_ip_address'] = found_tor['management']['management_ipv6_address']

            # Remove network_attach_group from net if the group_name is not defined
            for net in data_model['vxlan']['overlay']['networks']:
                if 'network_attach_group' in net:
                    if net.get('network_attach_group') not in net_grp_name_list:
                        del net['network_attach_group']

        if data_model['vxlan']['fabric']['type'] in ('MSD', 'MCFG'):
            # Rebuild sm_data['vxlan']['multisite']['overlay']['vrf_attach_groups'] into
            # a structure that is easier to use.
            vrf_grp_name_list = []
            data_model['vxlan']['multisite']['overlay']['vrf_attach_groups_dict'] = {}
            data_model['vxlan']['multisite']['overlay']['vrf_attach_switches_list'] = []
            for grp in data_model['vxlan']['multisite']['overlay']['vrf_attach_groups']:
                data_model['vxlan']['multisite']['overlay']['vrf_attach_groups_dict'][grp['name']] = []
                vrf_grp_name_list.append(grp['name'])
                for switch in grp['switches']:
                    data_model['vxlan']['multisite']['overlay']['vrf_attach_groups_dict'][grp['name']].append(switch)
                # If the switch is in the switch list and a hostname is used, replace the hostname with the management IP
                for switch in data_model['vxlan']['multisite']['overlay']['vrf_attach_groups_dict'][grp['name']]:
                    if any(sw['name'] == switch['hostname'] for sw in switches):
                        found_switch = next((item for item in switches if item["name"] == switch['hostname']))
                        if found_switch.get('management').get('management_ipv4_address'):
                            switch['mgmt_ip_address'] = found_switch['management']['management_ipv4_address']
                        elif found_switch.get('management').get('management_ipv6_address'):
                            switch['mgmt_ip_address'] = found_switch['management']['management_ipv6_address']

                    # Append switch to a flat list of switches for cross comparison later when we query the
                    # MSD fabric information.  We need to stop execution if the list returned by the MSD query
                    # does not include one of these switches.
                    data_model['vxlan']['multisite']['overlay']['vrf_attach_switches_list'].append(switch['hostname'])

            # Remove vrf_attach_group from vrf if the group_name is not defined
            for vrf in data_model['vxlan']['multisite']['overlay']['vrfs']:
                if 'vrf_attach_group' in vrf:
                    if vrf.get('vrf_attach_group') not in vrf_grp_name_list:
                        del vrf['vrf_attach_group']

            # Rebuild sm_data['vxlan']['overlay']['network_attach_groups'] into
            # a structure that is easier to use.
            net_grp_name_list = []
            data_model['vxlan']['multisite']['overlay']['network_attach_groups_dict'] = {}
            data_model['vxlan']['multisite']['overlay']['network_attach_switches_list'] = []
            for grp in data_model['vxlan']['multisite']['overlay']['network_attach_groups']:
                data_model['vxlan']['multisite']['overlay']['network_attach_groups_dict'][grp['name']] = []
                net_grp_name_list.append(grp['name'])
                for switch in grp['switches']:
                    data_model['vxlan']['multisite']['overlay']['network_attach_groups_dict'][grp['name']].append(switch)
                # If the switch is in the switch list and a hostname is used, replace the hostname with the management IP
                for switch in data_model['vxlan']['multisite']['overlay']['network_attach_groups_dict'][grp['name']]:
                    if any(sw['name'] == switch['hostname'] for sw in switches):
                        found_switch = next((item for item in switches if item["name"] == switch['hostname']))
                        if found_switch.get('management').get('management_ipv4_address'):
                            switch['mgmt_ip_address'] = found_switch['management']['management_ipv4_address']
                        elif found_switch.get('management').get('management_ipv6_address'):
                            switch['mgmt_ip_address'] = found_switch['management']['management_ipv6_address']

                    # Process nested TOR entries and resolve their management IPs
                    if 'tors' in switch and switch['tors']:
                        for tor in switch['tors']:
                            tor_hostname = tor.get('hostname')
                            if tor_hostname and any(sw['name'] == tor_hostname for sw in switches):
                                found_tor = next((item for item in switches if item["name"] == tor_hostname))
                                if found_tor.get('management').get('management_ipv4_address'):
                                    tor['mgmt_ip_address'] = found_tor['management']['management_ipv4_address']
                                elif found_tor.get('management').get('management_ipv6_address'):
                                    tor['mgmt_ip_address'] = found_tor['management']['management_ipv6_address']

                    # Append switch to a flat list of switches for cross comparison later when we query the
                    # MSD fabric information.  We need to stop execution if the list returned by the MSD query
                    # does not include one of these switches.
                    data_model['vxlan']['multisite']['overlay']['network_attach_switches_list'].append(switch['hostname'])

            # Remove network_attach_group from net if the group_name is not defined
            for net in data_model['vxlan']['multisite']['overlay']['networks']:
                if 'network_attach_group' in net:
                    if net.get('network_attach_group') not in net_grp_name_list:
                        del net['network_attach_group']

        self.kwargs['results']['model_extended'] = data_model
        return self.kwargs['results']

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

# Count interfaces of different types and expose in extended service model for controls within playbooks
#
import re


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []
        # interface modes which are a direct match
        self.mode_direct = ['routed', 'routed_po', 'routed_sub', 'loopback', 'fabric_loopback', 'mpls_loopback']
        # interface modes which need additional validation
        self.mode_indirect = ['access', 'dot1q', 'trunk', 'access_po', 'trunk_po', 'access_vpc', 'trunk_vpc', 'all']

    def prepare(self):
        data_model = self.kwargs['results']['model_extended']

        # This plugin does not apply to the follwing fabric types
        if data_model['vxlan']['fabric']['type'] in ['MSD', 'MCFG']:
            return self.kwargs['results']

        data_model['vxlan']['topology']['interfaces'] = {}
        data_model['vxlan']['topology']['interfaces']['modes'] = {}

        # Initialize breakout interfaces
        data_model['vxlan']['topology']['interfaces']['modes']['breakout'] = {}
        data_model['vxlan']['topology']['interfaces']['modes']['breakout']['count'] = 0

        # Initialize breakout preprovisioned interfaces
        data_model['vxlan']['topology']['interfaces']['modes']['breakout_preprov'] = {}
        data_model['vxlan']['topology']['interfaces']['modes']['breakout_preprov']['count'] = 0

        loopback_id = []
        if data_model['vxlan'].get('underlay', {}).get('general', {}).get('manual_underlay_allocation'):
            loopback_id.append(data_model['vxlan']['underlay']['general']['underlay_routing_loopback_id'])
            loopback_id.append(data_model['vxlan']['underlay']['general']['underlay_vtep_loopback_id'])

        # loop through interface modes and initialize with interface count 0
        for mode in self.mode_direct:
            data_model['vxlan']['topology']['interfaces']['modes'][mode] = {}
            data_model['vxlan']['topology']['interfaces']['modes'][mode]['count'] = 0
        for mode in self.mode_indirect:
            data_model['vxlan']['topology']['interfaces']['modes'][mode] = {}
            data_model['vxlan']['topology']['interfaces']['modes'][mode]['count'] = 0

        for switch in data_model.get('vxlan').get('topology').get('switches'):
            # loop through interfaces
            for interface in switch.get('interfaces'):
                # loop through interface modes direct and count
                for interface_mode in self.mode_direct:
                    # if interface mode is a direct match, then increment the count for that mode
                    if interface_mode == interface.get('mode'):
                        # Add special condition to exclude fabric loopback when manual_allocation is enabled
                        # Match interface names like 'lo<ID>' or 'loopback<ID>', where <ID> is an integer
                        loopback_regex = re.compile(r'^(lo|loopback)(\d+)$', re.IGNORECASE)
                        if not (
                            interface.get('mode') == 'fabric_loopback'
                            and (
                                loopback_regex.match(interface.get('name'))
                                and int(loopback_regex.match(interface.get('name')).group(2)) in loopback_id
                            )
                        ):
                            data_model['vxlan']['topology']['interfaces']['modes'][interface_mode]['count'] += 1
                            data_model['vxlan']['topology']['interfaces']['modes']['all']['count'] += 1
                # loop through interface modes indirect along with additional validation and count
                if interface.get('mode') == 'access':
                    # if interface name starts with 'po' and has vpc_id, then it is a vpc access interface
                    if interface.get('name').lower().startswith('po') and interface.get('vpc_id'):
                        data_model['vxlan']['topology']['interfaces']['modes']['access_vpc']['count'] += 1
                        data_model['vxlan']['topology']['interfaces']['modes']['all']['count'] += 1
                    # if interface name starts with 'po', then it is a port-channel access interface
                    elif interface.get('name').lower().startswith('po'):
                        data_model['vxlan']['topology']['interfaces']['modes']['access_po']['count'] += 1
                        data_model['vxlan']['topology']['interfaces']['modes']['all']['count'] += 1
                    # else it is a regular access interface
                    else:
                        data_model['vxlan']['topology']['interfaces']['modes']['access']['count'] += 1
                        data_model['vxlan']['topology']['interfaces']['modes']['all']['count'] += 1
                if interface.get('mode') == 'dot1q':
                    data_model['vxlan']['topology']['interfaces']['modes']['dot1q']['count'] += 1
                    data_model['vxlan']['topology']['interfaces']['modes']['all']['count'] += 1
                if interface.get('mode') == 'trunk':
                    # if interface name starts with 'po' and has vpc_id, then it is a vpc trunk interface
                    if interface.get('name').lower().startswith('po') and interface.get('vpc_id'):
                        data_model['vxlan']['topology']['interfaces']['modes']['trunk_vpc']['count'] += 1
                        data_model['vxlan']['topology']['interfaces']['modes']['all']['count'] += 1
                    # if interface name starts with 'po', then it is a port-channel trunk interface
                    elif interface.get('name').lower().startswith('po'):
                        data_model['vxlan']['topology']['interfaces']['modes']['trunk_po']['count'] += 1
                        data_model['vxlan']['topology']['interfaces']['modes']['all']['count'] += 1
                    # else it is a regular trunk interface
                    else:
                        data_model['vxlan']['topology']['interfaces']['modes']['trunk']['count'] += 1
                        data_model['vxlan']['topology']['interfaces']['modes']['all']['count'] += 1

            if switch.get('interface_breakouts'):
                for breakout in switch.get('interface_breakouts'):
                    if breakout.get('enable_during_bootstrap') in [False, None]:
                        if breakout.get('to'):
                            nb_int = breakout['to'] - breakout['from']
                            data_model['vxlan']['topology']['interfaces']['modes']['breakout']['count'] += nb_int + 1
                        else:
                            data_model['vxlan']['topology']['interfaces']['modes']['breakout']['count'] += 1

                    if breakout.get('enable_during_bootstrap') is True:
                        if breakout.get('to'):
                            nb_int = breakout['to'] - breakout['from']
                            data_model['vxlan']['topology']['interfaces']['modes']['breakout_preprov']['count'] += nb_int + 1
                        else:
                            data_model['vxlan']['topology']['interfaces']['modes']['breakout_preprov']['count'] += 1

        self.kwargs['results']['model_extended'] = data_model
        return self.kwargs['results']

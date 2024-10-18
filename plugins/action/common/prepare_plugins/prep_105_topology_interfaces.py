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
class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []
        # interface modes which are a direct match
        self.mode_direct = ['routed', 'routed_po', 'routed_sub', 'loopback', 'fabric_loopback', 'mpls_loopback']
        # interface modes which need additional validation
        self.mode_indirect = ['access', 'trunk', 'access_po', 'trunk_po', 'access_vpc', 'trunk_vpc', 'all']

    def prepare(self):
        model_data = self.kwargs['results']['model_extended']

        if model_data['vxlan'].get('topology', None) is not None:
            model_data['vxlan']['topology']['interfaces'] = {}
            model_data['vxlan']['topology']['interfaces']['modes'] = {}

            # loop through interface modes and initialize with interface count 0
            for mode in self.mode_direct:
                model_data['vxlan']['topology']['interfaces']['modes'][mode] = {}
                model_data['vxlan']['topology']['interfaces']['modes'][mode]['count'] = 0
            for mode in self.mode_indirect:
                model_data['vxlan']['topology']['interfaces']['modes'][mode] = {}
                model_data['vxlan']['topology']['interfaces']['modes'][mode]['count'] = 0

            for switch in model_data.get('vxlan').get('topology').get('switches'):
                # loop through interfaces
                for interface in switch.get('interfaces'):
                    # loop through interface modes direct and count
                    for interface_mode in self.mode_direct:
                        # if interface mode is a direct match, then increment the count for that mode
                        if interface_mode == interface.get('mode'):
                            model_data['vxlan']['topology']['interfaces']['modes'][interface_mode]['count'] += 1
                            model_data['vxlan']['topology']['interfaces']['modes']['all']['count'] += 1
                    # loop through interface modes indirect along with additional validation and count
                    if interface.get('mode') == 'access':
                        # if interface name starts with 'po' and has vpc_id, then it is a vpc access interface
                        if interface.get('name').lower().startswith('po') and interface.get('vpc_id'):
                            model_data['vxlan']['topology']['interfaces']['modes']['access_vpc']['count'] += 1
                            model_data['vxlan']['topology']['interfaces']['modes']['all']['count'] += 1
                        # if interface name starts with 'po', then it is a port-channel access interface
                        elif interface.get('name').lower().startswith('po'):
                            model_data['vxlan']['topology']['interfaces']['modes']['access_po']['count'] += 1
                            model_data['vxlan']['topology']['interfaces']['modes']['all']['count'] += 1
                        # else it is a regular access interface
                        else:
                            model_data['vxlan']['topology']['interfaces']['modes']['access']['count'] += 1
                            model_data['vxlan']['topology']['interfaces']['modes']['all']['count'] += 1
                    if interface.get('mode') == 'trunk':
                        # if interface name starts with 'po' and has vpc_id, then it is a vpc trunk interface
                        if interface.get('name').lower().startswith('po') and interface.get('vpc_id'):
                            model_data['vxlan']['topology']['interfaces']['modes']['trunk_vpc']['count'] += 1
                            model_data['vxlan']['topology']['interfaces']['modes']['all']['count'] += 1
                        # if interface name starts with 'po', then it is a port-channel trunk interface
                        elif interface.get('name').lower().startswith('po'):
                            model_data['vxlan']['topology']['interfaces']['modes']['trunk_po']['count'] += 1
                            model_data['vxlan']['topology']['interfaces']['modes']['all']['count'] += 1
                        # else it is a regular trunk interface
                        else:
                            model_data['vxlan']['topology']['interfaces']['modes']['trunk']['count'] += 1
                            model_data['vxlan']['topology']['interfaces']['modes']['all']['count'] += 1

        self.kwargs['results']['model_extended'] = model_data
        return self.kwargs['results']

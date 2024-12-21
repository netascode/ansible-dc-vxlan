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

from ....plugin_utils.helper_functions import hostname_to_ip_mapping


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        model_data = self.kwargs['results']['model_extended']
        #  Loop over all the roles in vxlan.topology.switches.role
        model_data['vxlan']['topology']['spine'] = {}
        model_data['vxlan']['topology']['leaf'] = {}
        model_data['vxlan']['topology']['border'] = {}
        model_data['vxlan']['topology']['border_spine'] = {}
        model_data['vxlan']['topology']['border_gateway'] = {}
        model_data['vxlan']['topology']['border_gateway_spine'] = {}
        model_data['vxlan']['topology']['super_spine'] = {}
        model_data['vxlan']['topology']['border_super_spine'] = {}
        model_data['vxlan']['topology']['border_gateway_super_spine'] = {}
        model_data['vxlan']['topology']['tor'] = {}
        model_data['vxlan']['topology']['core_router'] = {}
        sm_switches = model_data['vxlan']['topology']['switches']
        for switch in sm_switches:
            # Build list of switch IP's based on role keyed by switch name
            name = switch.get('name')
            role = switch.get('role')
            model_data['vxlan']['topology'][role][name] = {}
            v4_key = 'management_ipv4_address'
            v6_key = 'management_ipv6_address'
            v4ip = switch.get('management').get(v4_key)
            v6ip = switch.get('management').get(v6_key)
            model_data['vxlan']['topology'][role][name][v4_key] = v4ip
            model_data['vxlan']['topology'][role][name][v6_key] = v6ip

        model_data = hostname_to_ip_mapping(model_data)

        self.kwargs['results']['model_extended'] = model_data

        return self.kwargs['results']

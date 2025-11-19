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

        # This plugin does not apply to the follwing fabric types
        if data_model['vxlan']['fabric']['type'] in ['MSD', 'MFD']:
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

        self.kwargs['results']['model_extended'] = data_model
        return self.kwargs['results']

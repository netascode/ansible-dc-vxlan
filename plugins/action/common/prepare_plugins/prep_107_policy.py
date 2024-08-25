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

        # import epdb; epdb.st()

        # Ensure that vrf_lite's switches are mappinged to their respective 
        # management IP address from topology switches
        topology_switches = model_data['vxlan']['topology']['switches']
        policy_switches = model_data['vxlan']['policy']['switches']
        for switch in policy_switches:
            if any(sw['name'] == switch['name'] for sw in topology_switches):
                found_switch = next((item for item in topology_switches if item["name"] == switch['name']))
                if found_switch.get('management').get('management_ipv4_address'):
                    switch['name'] = found_switch['management']['management_ipv4_address']
                elif found_switch.get('management').get('management_ipv6_address'):
                    switch['name'] = found_switch['management']['management_ipv6_address']

        self.kwargs['results']['model_extended'] = model_data
        return self.kwargs['results']

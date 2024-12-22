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

from ansible.utils.display import Display
from ....plugin_utils.helper_functions import data_model_key_check
from ....plugin_utils.data_model_keys import model_keys

display = Display()


def update_nested_dict(nested_dict, keys, new_value):
    if len(keys) == 1:
        nested_dict[keys[0]] = new_value
    else:
        key = keys[0]
        if key in nested_dict:
            update_nested_dict(nested_dict[key], keys[1:], new_value)


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def set_list_default(self, parent_keys, target_key):
        keys = parent_keys + [target_key]
        dm_check = data_model_key_check(self.model_data, keys)
        if target_key in dm_check['keys_not_found'] or \
           target_key in dm_check['keys_no_data']:
            update_nested_dict(self.model_data, keys, [])

    # The prepare method is used to default each list or nested list
    # in the model data to an empty list if the key for the list does
    # not exist or data under they key does not exist.
    #
    # This is to ensure that the model data is consistent and can be
    # used by other plugins without having to check if the key exists.
    def prepare(self):
        self.model_data = self.kwargs['results']['model_extended']

        # --------------------------------------------------------------------
        # Fabric Global List Defaults
        # --------------------------------------------------------------------
        from pprint import pprint

        paths = [
            'global.dns_servers',
            'global.ntp_servers',
            'global.syslog_servers',
            'global.spanning_tree',
            'global.spanning_tree.vlan_range',
            'global.spanning_tree.mst_instance_range',
            'global.netflow',
            'global.netflow.exporter',
            'global.netflow.record',
            'global.netflow.monitor',
            'underlay',
            'topology',
            'topology.edge_connections',
            'topology.fabric_links',
            'topology.switches',
            'topology.vpc_peers',
            'overlay',
            'overlay.vrfs',
            'overlay.vrf_attach_groups',
            'overlay.networks',
            'overlay.network_attach_groups',
            'multisite',
            'multisite.overlay',
            'multisite.overlay.vrfs',
            'multisite.overlay.vrf_attach_groups',
            'multisite.overlay.networks',
            'multisite.overlay.network_attach_groups',
            'policy',
            'policy.policies',
            'policy.groups',
            'policy.switches'
        ]
        for path in paths:
            # Get all but the last 2 elements of model_keys[path]
            path_type = model_keys[path][-1]
            parent_keys = model_keys[path][:-2]
            target_key = model_keys[path][-2]
            if path_type == 'KEY':
                dm_check = data_model_key_check(self.model_data, parent_keys + [target_key])
                if target_key in dm_check['keys_not_found'] or target_key in dm_check['keys_no_data']:
                    update_nested_dict(self.model_data, parent_keys + [target_key], {})
            if path_type == 'LIST':
                self.set_list_default(parent_keys, target_key)

        # --------------------------------------------------------------------
        # The following sections deal with more difficult nexted list
        # structures where there is a list_index in the middle of the dict.
        # There may be a way to reduce the amount of code but for now leaving
        # it as is.
        # --------------------------------------------------------------------

        # --------------------------------------------------------------------
        # Fabric Topology Switches Freeforms List Defaults
        # --------------------------------------------------------------------

        # Check vxlan.topology.switches[index].freeforms list elements
        list_index = 0
        for switch in self.model_data['vxlan']['topology']['switches']:
            dm_check = data_model_key_check(switch, ['freeforms'])
            if 'freeforms' in dm_check['keys_not_found'] or \
               'freeforms' in dm_check['keys_no_data']:
                self.model_data['vxlan']['topology']['switches'][list_index]['freeforms'] = []

            list_index += 1

        # --------------------------------------------------------------------
        # Fabric Topology Switches Interfaces List Defaults
        # --------------------------------------------------------------------

        # Check vxlan.topology.switches[index].interfaces list elements
        list_index = 0
        for switch in self.model_data['vxlan']['topology']['switches']:
            dm_check = data_model_key_check(switch, ['interfaces'])
            if 'interfaces' in dm_check['keys_not_found'] or 'interfaces' in dm_check['keys_no_data']:
                self.model_data['vxlan']['topology']['switches'][list_index]['interfaces'] = []

            list_index += 1

        # --------------------------------------------------------------------
        # Fabric Overlay vrf and network attach group List Defaults
        # --------------------------------------------------------------------

        # Check vxlan.overlay.vrf_attach_groups[index].switches list elements
        list_index = 0
        for group in self.model_data['vxlan']['overlay']['vrf_attach_groups']:
            dm_check = data_model_key_check(group, ['switches'])
            if 'switches' in dm_check['keys_not_found'] or \
               'switches' in dm_check['keys_no_data']:
                self.model_data['vxlan']['overlay']['vrf_attach_groups'][list_index]['switches'] = []

            list_index += 1

        # Check vxlan.overlay.network_attach_groups[index].switches list elements
        list_index = 0
        for group in self.model_data['vxlan']['overlay']['network_attach_groups']:
            dm_check = data_model_key_check(group, ['switches'])
            if 'switches' in dm_check['keys_not_found'] or \
               'switches' in dm_check['keys_no_data']:
                self.model_data['vxlan']['overlay']['network_attach_groups'][list_index]['switches'] = []

            list_index += 1

        # Check vxlan.multisite.overlay.vrf_attach_groups[index].switches list elements
        list_index = 0
        for group in self.model_data['vxlan']['multisite']['overlay']['vrf_attach_groups']:
            dm_check = data_model_key_check(group, ['switches'])
            if 'switches' in dm_check['keys_not_found'] or \
               'switches' in dm_check['keys_no_data']:
                self.model_data['vxlan']['multisite']['overlay']['vrf_attach_groups'][list_index]['switches'] = []

            list_index += 1

        # Check vxlan.multisite.overlay.network_attach_groups[index].switches list elements
        list_index = 0
        for group in self.model_data['vxlan']['multisite']['overlay']['network_attach_groups']:
            dm_check = data_model_key_check(group, ['switches'])
            if 'switches' in dm_check['keys_not_found'] or \
               'switches' in dm_check['keys_no_data']:
                self.model_data['vxlan']['multisite']['overlay']['network_attach_groups'][list_index]['switches'] = []

            list_index += 1

        # Before returning check to see if global or underlay data is present and
        # generate a warning if they are empty.  There might actualy be data but
        # one of the other model files might have a bug or everything except the
        # top level vxlan key is commented out.
        if not bool(self.model_data['vxlan']['underlay']):
            msg = '((vxlan.underlay)) data is empty! Check your host_vars model data.'
            display.warning(msg=msg, formatted=True)
        if not bool(self.model_data['vxlan']['global']):
            msg = '((vxlan.global)) data is empty! Check your host_vars model data.'
            display.warning(msg=msg, formatted=True)

        self.kwargs['results']['model_extended'] = self.model_data
        return self.kwargs['results']

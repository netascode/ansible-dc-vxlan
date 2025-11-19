# Copyright (c) 2025 Cisco Systems, Inc. and its affiliates
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


# Convert schema values of L2 MTU interfaces to the required format ('default' or 'jumbo')

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import data_model_key_check
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import normalize_interface_name


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def get_parent_interface_name_mtu(self, sub_interface_name, switch_interfaces, default_routed_int_mtu, default_port_channel_mtu):
        parent_interface_name = normalize_interface_name(sub_interface_name).split('.')[0]
        parent_interface_mtu = 0
        for interface in switch_interfaces:
            if parent_interface_name == normalize_interface_name(interface.get('name')):
                if interface.get('mtu'):
                    parent_interface_mtu = interface.get('mtu')
                    break
        if not parent_interface_mtu:
            if 'Port-channel' in parent_interface_name:
                parent_interface_mtu = default_port_channel_mtu
            else:
                parent_interface_mtu = default_routed_int_mtu
        return parent_interface_name, parent_interface_mtu

    # layer2_host_interface_mtu must be an even int
    def standarize_global_l2_mtu(self, mtu):
        n = None
        match mtu:
            case 'default':
                return 1500
            case int(n) if n % 2 == 0:
                return mtu
            case _:
                self.kwargs['results']['failed'] = True
                self.kwargs['results']['msg'] = f'vxlan.underlay.general.layer2_host_interface_mtu is not a valid value ({mtu}). MTU cannot be an odd number.'

    # Validate that the interfaces mtu is correct, either 1500 or the value of layer2_host_interface_mtu (sysmtem jumbomtu)
    def standarize_l2_mtu(self, switch_name, interface, system_mtu):
        n = None
        interface_mtu = interface.get('mtu')
        interface_name = normalize_interface_name(interface.get('name'))
        match interface_mtu:
            case 1500:
                return 'default'
            case int(n) if n == system_mtu:
                return 'jumbo'
            case str(n) if n in ('jumbo', 'default'):
                return interface_mtu
            case _:
                self.kwargs['results']['failed'] = True
                # Adding space if previous errors exist if not initialize str
                if self.kwargs['results']['msg']:
                    self.kwargs['results']['msg'] += ' '
                else:
                    self.kwargs['results']['msg'] = ''

                self.kwargs['results']['msg'] += f'vxlan.topology.switches.{switch_name}.interfaces.{interface_name}.mtu ({interface_mtu}) is not a valid \
value. MTU must be 1500 or {system_mtu}.'
                return None

    def prepare(self):
        model_data = self.kwargs['results']['model_extended']
        l2_jumbomtu = self.kwargs['default_values']['vxlan']['underlay']['general']['layer2_host_interface_mtu']
        default_sub_interface_mtu = self.kwargs['default_values']['vxlan']['topology']['switches']['interfaces']['topology_switch_routed_sub_interface']['mtu']
        default_routed_int_mtu = self.kwargs['default_values']['vxlan']['topology']['switches']['interfaces']['topology_switch_routed_interface']['mtu']
        default_port_channel_mtu = self.kwargs['default_values']['vxlan']['topology']['switches']['interfaces']['topology_switch_routed_po_interface']['mtu']

        dm_check = data_model_key_check(model_data, ['vxlan', 'underlay', 'general'])

        # Check if vxlan.underlay.general is defined
        if 'general' in dm_check['keys_data']:
            if 'layer2_host_interface_mtu' in model_data['vxlan']['underlay']['general']:
                l2_host_interface_mtu = model_data['vxlan']['underlay']['general']['layer2_host_interface_mtu']
                l2_host_interface_mtu_standardized = self.standarize_global_l2_mtu(l2_host_interface_mtu)
                model_data['vxlan']['underlay']['general']['layer2_host_interface_mtu'] = l2_host_interface_mtu_standardized
                l2_jumbomtu = l2_host_interface_mtu_standardized

            if 'intra_fabric_interface_mtu' in model_data['vxlan']['underlay']['general']:
                intra_fabric_interface_mtu = model_data['vxlan']['underlay']['general']['intra_fabric_interface_mtu']
                # intra_fabric_interface_mtu must be an even int
                if intra_fabric_interface_mtu % 2 != 0:
                    self.kwargs['results']['failed'] = True

                    # Adding space if previous errors exist if not initialize str
                    if self.kwargs['results']['msg']:
                        self.kwargs['results']['msg'] += ' '
                    else:
                        self.kwargs['results']['msg'] = ''

                    self.kwargs['results']['msg'] += f'vxlan.underlay.general.intra_fabric_interface_mtu is not a valid value \
({intra_fabric_interface_mtu}). MTU cannot be an odd number.'

        dm_check = data_model_key_check(model_data, ['vxlan', 'topology', 'switches'])

        # Check if vxlan.topology is defined
        if 'switches' in dm_check['keys_data']:
            for switch_index, switch in enumerate(model_data.get('vxlan').get('topology').get('switches')):

                switch_name = switch.get('name')

                # loop through interfaces
                for interface_index, interface in enumerate(switch.get('interfaces')):
                    interface_mode = interface.get('mode')
                    interface_name = normalize_interface_name(interface.get('name'))

                    # L2 interfaces
                    if interface_mode in ['access', 'trunk', 'dot1q']:
                        if interface.get('mtu'):
                            interface_mtu = self.standarize_l2_mtu(switch_name, interface, l2_jumbomtu)
                            model_data['vxlan']['topology']['switches'][switch_index]['interfaces'][interface_index]['mtu'] = interface_mtu

                    # L3 interfaces
                    if interface_mode in ['routed', 'routed_po', 'routed_sub']:
                        if interface.get('mtu'):
                            interface_mtu = interface.get('mtu')
                            # MTU must be an even number
                            if interface_mtu % 2 != 0:
                                self.kwargs['results']['failed'] = True
                                # Adding space if previous errors exist if not initialize str
                                if self.kwargs['results']['msg']:
                                    self.kwargs['results']['msg'] += ' '
                                else:
                                    self.kwargs['results']['msg'] = ''

                                self.kwargs['results']['msg'] += f'vxlan.topology.switches.{switch_name}.interfaces.{interface_name} is not a valid value \
({interface_mtu}). MTU cannot be an odd number.'

                    # Sub interfaces
                    if interface_mode == 'routed_sub':
                        parent_interface_name, parent_interface_mtu = self.get_parent_interface_name_mtu(interface_name, switch.get('interfaces'),
                                                                                                         default_routed_int_mtu,
                                                                                                         default_port_channel_mtu)
                        sub_interface_mtu = interface.get('mtu') if interface.get('mtu') else default_sub_interface_mtu
                        if parent_interface_mtu < sub_interface_mtu:
                            self.kwargs['results']['failed'] = True
                        # Adding space if previous errors exist if not initialize str
                            if self.kwargs['results']['msg']:
                                self.kwargs['results']['msg'] += ' '
                            else:
                                self.kwargs['results']['msg'] = ''

                            self.kwargs['results']['msg'] += f'vxlan.topology.switches.{switch_name}.interfaces.\
{normalize_interface_name(interface_name)}.mtu is not a valid value. {normalize_interface_name(interface_name)} MTU ({sub_interface_mtu}) \
cannot be greater than {parent_interface_name} MTU ({parent_interface_mtu}).'

        self.kwargs['results']['model_extended'] = model_data
        return self.kwargs['results']

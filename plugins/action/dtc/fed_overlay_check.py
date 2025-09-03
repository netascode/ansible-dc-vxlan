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

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase

display = Display()


class ActionModule(ActionBase):
    """
    This class is used to compare the existing links with the links that you are
    looking to add to the fabric. If the link already exists, it will be added to
    the not_required_links list.
    """
    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        check_type = self._task.args['check_type']
        model_data = self._task.args['model_data']
        normal_model_data = []
        ndfc_data = self._task.args['ndfc_data']
        ndfc_attachment_data = self._task.args['ndfc_attachment_data']
        normal_ndfc_data = []
        restructured_data = []
        restructured_attachment_data = []
        deployment = False
        deploy_payload = []
        # normalise data for comparison
        if check_type == 'network_attach':
            switch_data = ndfc_data
            for attached_network in ndfc_attachment_data:
                for network_attached_group in attached_network['lanAttachList']:
                    if network_attached_group['isLanAttached'] is True:
                        normal_ndfc_data.append({
                            'networkName': network_attached_group['networkName'],
                            'switchName': network_attached_group['switchName'],
                            'serialNumber': network_attached_group['switchSerialNo'],
                            'portNames': network_attached_group['portNames'],
                            'deployment': deployment,
                            'fabric': network_attached_group['fabricName']
                        })
            for network in model_data['vxlan']['multisite']['overlay']['networks']:
                for network_attach_group in model_data['vxlan']['multisite']['overlay']['network_attach_groups']:
                    if network.get('network_attach_group') == network_attach_group['name']:
                        for switch in network_attach_group['switches']:
                            for switch_entry in switch_data:
                                if switch['hostname'] == switch_entry['logicalName']:
                                    if switch.get('tors'):
                                        main = f"{switch['hostname']}({','.join(switch['ports'])})"
                                        # Format each tor entry
                                        tors = ' '.join(
                                            f"{tor['hostname']}({','.join(tor['ports'])})"
                                            for tor in switch.get('tors', [])
                                        )
                                        # Combine main and tors
                                        ports = f"{main} {tors}".strip()

                                        normal_model_data.append({
                                            'networkName': network['name'],
                                            'switchName': switch['hostname'],
                                            'serialNumber': switch_entry['serialNumber'],
                                            'portNames': ports,
                                            'deployment': deployment,
                                            'fabric': switch_entry['fabricName']
                                        })
                                    else:
                                        normal_model_data.append({
                                            'networkName': network['name'],
                                            'switchName': switch['hostname'],
                                            'serialNumber': switch_entry['serialNumber'],
                                            'portNames': (",".join(switch['ports'])),
                                            'deployment': deployment,
                                            'fabric': switch_entry['fabricName']
                                        })
            difference = [item for item in normal_ndfc_data if item not in normal_model_data]

            # Restructure in case of just port removal
            for item in difference:
                if item['portNames'] != "":
                    for network in model_data['vxlan']['multisite']['overlay']['networks']:
                        for network_attach_group in model_data['vxlan']['multisite']['overlay']['network_attach_groups']:
                            if network.get('network_attach_group') == network_attach_group['name'] and item['networkName'] == network['name']:
                                for switch in network_attach_group['switches']:
                                    if switch['hostname'] == item['switchName']:
                                        port_difference = [port for port in item['portNames'].split(',') if port not in switch['ports']]
                                        if switch.get('ports'):
                                            item['switchPorts'] = ",".join(switch['ports'])
                                        else:
                                            item['switchPorts'] = ""
                                        item['detachSwitchPorts'] = ",".join(port_difference)
                                        item['deployment'] = True
                                        item.pop('portNames')
            # psuedo code for vpc pair removal when only 1 switch has changes
            # for switches in nddfc ndfc_data
            #     if switch in ndfc has vpc = true and switch hostname = difference switch hostname
            #         if found vpc serial is not in difference:
            #             add vpc paired device payloiad from ndfc ndfc_data

            # Restructure the difference data into payload format
            network_dict = {}
            for item in difference:
                network_name = item['networkName']
                if network_name not in network_dict:
                    network_dict[network_name] = {'networkName': network_name, 'lanAttachList': []}
                network_dict[network_name]['lanAttachList'].append(item)
                deploy_payload.append(item['serialNumber'])
            restructured_attachment_data = list(network_dict.values())

        if check_type == 'network':
            network_attachment_dict = {}
            for network in model_data['vxlan']['multisite']['overlay']['networks']:
                normal_model_data.append(network['name'])
            for network in ndfc_data:
                normal_ndfc_data.append(network['networkName'])
            network_difference = [network for network in normal_ndfc_data if network not in normal_model_data]
            restructured_data = network_difference
            for network in network_difference:
                for attached_network in ndfc_attachment_data:
                    for network_attached_group in attached_network['lanAttachList']:
                        if (network == attached_network['networkName'] and
                                network == network_attached_group['networkName'] and
                                network_attached_group['isLanAttached'] is True):
                            if network not in network_attachment_dict:
                                network_attachment_dict[network] = {
                                    'networkName': network,
                                    'lanAttachList': []
                                }
                            network_attachment_dict[network]['lanAttachList'].append({
                                'networkName': network_attached_group['networkName'],
                                'switchName': network_attached_group['switchName'],
                                'serialNumber': network_attached_group['switchSerialNo'],
                                'portNames': network_attached_group['portNames'],
                                'deployment': deployment,
                                'fabric': network_attached_group['fabricName']
                            })
                            network_attachment_dict[network]['lanAttachList'].append({
                                'networkName': network_attached_group['networkName'],
                                'switchName': network_attached_group['switchName'],
                                'serialNumber': network_attached_group['switchSerialNo'],
                                'portNames': network_attached_group['portNames'],
                                'deployment': deployment,
                                'fabric': network_attached_group['fabricName']
                            })
                            deploy_payload.append(network_attached_group['switchSerialNo'])
            restructured_attachment_data = list(network_attachment_dict.values())

        elif check_type == 'vrf_attach':
            switch_data = ndfc_data
            for attached_vrf in ndfc_attachment_data:
                for vrf_attached_group in attached_vrf['lanAttachList']:
                    if vrf_attached_group['isLanAttached'] is True:
                        normal_ndfc_data.append({
                            'fabric': vrf_attached_group['fabricName'],
                            'deployment': deployment,
                            'vrfName': vrf_attached_group['vrfName'],
                            'serialNumber': vrf_attached_group['switchSerialNo']
                        })
            for vrf in model_data['vxlan']['multisite']['overlay']['vrfs']:
                for vrf_attach_group in model_data['vxlan']['multisite']['overlay']['vrf_attach_groups']:
                    if vrf['vrf_attach_group'] == vrf_attach_group['name']:
                        for switch in vrf_attach_group['switches']:
                            for switch_entry in switch_data:
                                if switch['hostname'] == switch_entry['logicalName']:
                                    normal_model_data.append({
                                        'fabric': switch_entry['fabricName'],
                                        'deployment': deployment,
                                        'vrfName': vrf['name'],
                                        'serialNumber': switch_entry['serialNumber']
                                    })
            difference = [item for item in normal_ndfc_data if item not in normal_model_data]

            # Restructure the difference data
            vrf_dict = {}

            for item in difference:
                vrf_name = item['vrfName']
                if vrf_name not in vrf_dict:
                    vrf_dict[vrf_name] = {'vrfName': vrf_name, 'lanAttachList': []}
                vrf_dict[vrf_name]['lanAttachList'].append(item)
                deploy_payload.append(item['serialNumber'])
            restructured_attachment_data = list(vrf_dict.values())

        elif check_type == 'vrf':
            vrf_attachment_dict = {}
            for vrf in model_data['vxlan']['multisite']['overlay']['vrfs']:
                normal_model_data.append(vrf['name'])
            for vrf in ndfc_data:
                normal_ndfc_data.append(vrf['vrfName'])
            vrf_difference = [vrf for vrf in normal_ndfc_data if vrf not in normal_model_data]
            restructured_data = vrf_difference
            for vrf in vrf_difference:
                for attached_vrf in ndfc_attachment_data:
                    for vrf_attached_group in attached_vrf['lanAttachList']:
                        if vrf == attached_vrf['vrfName'] and vrf == vrf_attached_group['vrfName'] and vrf_attached_group['isLanAttached'] is True:
                            if vrf not in vrf_attachment_dict:
                                vrf_attachment_dict[vrf] = {'vrfName': vrf, 'lanAttachList': []}
                            vrf_attachment_dict[vrf]['lanAttachList'].append({
                                'vrfName': vrf_attached_group['vrfName'],
                                'serialNumber': vrf_attached_group['switchSerialNo'],
                                'deployment': deployment,
                                'fabric': vrf_attached_group['fabricName']
                            })
                            deploy_payload.append(vrf_attached_group['switchSerialNo'])
            restructured_attachment_data = list(vrf_attachment_dict.values())

        if deploy_payload != []:
            deploy_payload = set(deploy_payload)
        results['payload'] = restructured_data
        results['attachments_payload'] = restructured_attachment_data
        results['deploy_payload'] = deploy_payload

        return results

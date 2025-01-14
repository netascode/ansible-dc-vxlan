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
from ...plugin_utils.helper_functions import normalise_int_lists

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
        switch_data = self._task.args['switch_data']
        model_data = self._task.args['model_data']
        normal_model_data = []
        ndfc_data = self._task.args['ndfc_data']
        normal_ndfc_data = []
        payload = []
        if check_type == 'network_attach':
            for attached_network in ndfc_data: 
                for network_attached_group in attached_network['lanAttachList']:
                    if network_attached_group['isLanAttached'] == True:
                        normal_ndfc_data.append({'networkName': network_attached_group['networkName'],'switchName': network_attached_group['switchName'],'serialNumber':network_attached_group['switchSerialNo'],'portNames':normalise_int_lists(network_attached_group['portNames'])})
            for network in model_data['vxlan']['overlay_services']['networks']: 
                for network_attach_group in model_data['vxlan']['overlay_services']['networks_attach_groups']:
                    if network['network_attach_group'] == network_attach_group['name']:
                        for switch in network_attach_group['switches']:
                            for switch_entry in switch_data:
                                if switch['hostname'] == switch_entry['logical_name']:
                                    normal_model_data.append({'networkName':network['name'],'switchName':switch['hostname'],'serialNumber':switch_entry['serialNumber'],'portNames':normalise_int_lists(",".join(switch['ports']))})
        results['payload'] = payload
        return results
    
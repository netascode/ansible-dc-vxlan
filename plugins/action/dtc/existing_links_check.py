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
        existing_links = self._task.args['existing_links']
        fabric_links = self._task.args['fabric_links']
        switch_list = self._task.args['switch_data_model']
        required_links = []
        not_required_links = []
        for link in fabric_links:
            for existing_link in existing_links:
                if (
                    'sw1-info' in existing_link and
                    'sw2-info' in existing_link and
                    'sw-sys-name' in existing_link['sw1-info'] and
                    'sw-sys-name' in existing_link['sw2-info']
                ):
                    for switch in switch_list:
                        if existing_link['sw1-info']['sw-sys-name'].lower() == switch['name'].lower():
                            existing_link['sw1-info']['sw-sys-name'] = switch['management']['management_ipv4_address']
                        if existing_link['sw2-info']['sw-sys-name'].lower() == switch['name'].lower():
                            existing_link['sw2-info']['sw-sys-name'] = switch['management']['management_ipv4_address']
                    if ((existing_link['sw1-info']['sw-sys-name'].lower() == link['src_device'].lower() and
                         existing_link['sw1-info']['if-name'].lower() == link['src_interface'].lower() and
                         existing_link['sw2-info']['sw-sys-name'].lower() == link['dst_device'].lower() and
                         existing_link['sw2-info']['if-name'].lower() == link['dst_interface'].lower()) or
                        (existing_link['sw1-info']['sw-sys-name'].lower() == link['dst_device'].lower() and
                         existing_link['sw1-info']['if-name'].lower() == link['dst_interface'].lower() and
                         existing_link['sw2-info']['sw-sys-name'].lower() == link['src_device'].lower() and
                         existing_link['sw2-info']['if-name'].lower() == link['src_interface'].lower())):
                        if 'templateName' not in existing_link:
                            not_required_links.append(link)
                        elif existing_link['templateName'] == 'int_pre_provision_intra_fabric_link':
                            required_links.append(link)
                        elif existing_link['templateName'] == 'int_intra_fabric_num_link':
                            link['template'] = 'int_intra_fabric_num_link'
                            link['profile']['peer1_ipv4_addr'] = existing_link['nvPairs']['PEER1_IP']
                            link['profile']['peer2_ipv4_addr'] = existing_link['nvPairs']['PEER2_IP']
                            if existing_link.get('nvPairs').get('ENABLE_MACSEC'):
                                link['profile']['enable_macsec'] = existing_link['nvPairs']['ENABLE_MACSEC']
                            else:
                                link['profile']['enable_macsec'] = 'false'
                            required_links.append(link)
                        elif existing_link['templateName'] == 'int_intra_fabric_unnum_link':
                            required_links.append(link)
                    else:
                        not_required_links.append(link)
            if link not in required_links and link not in not_required_links:
                required_links.append(link)

        results['required_links'] = required_links
        return results

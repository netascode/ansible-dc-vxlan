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

                    # Check if the existing link matches the fabric link in either direction
                    if ((existing_link['sw1-info']['sw-sys-name'].lower() == link['src_device'].lower() and
                         existing_link['sw1-info']['if-name'].lower() == link['src_interface'].lower() and
                         existing_link['sw2-info']['sw-sys-name'].lower() == link['dst_device'].lower() and
                         existing_link['sw2-info']['if-name'].lower() == link['dst_interface'].lower()) or
                        (existing_link['sw1-info']['sw-sys-name'].lower() == link['dst_device'].lower() and
                         existing_link['sw1-info']['if-name'].lower() == link['dst_interface'].lower() and
                         existing_link['sw2-info']['sw-sys-name'].lower() == link['src_device'].lower() and
                         existing_link['sw2-info']['if-name'].lower() == link['src_interface'].lower())):

                        # If the link is in reverse order, swap the src and dst to match
                        # swap also in profile peer1 and peer2
                        # Don't swap IP addresses, bc they are assigned based on existing link
                        # and should not change
                        if (
                            existing_link['sw1-info']['sw-sys-name'].lower() == link['dst_device'].lower()
                            and existing_link['sw1-info']['if-name'].lower() == link['dst_interface'].lower()
                            and existing_link['sw2-info']['sw-sys-name'].lower() == link['src_device'].lower()
                            and existing_link['sw2-info']['if-name'].lower() == link['src_interface'].lower()
                        ):
                            link['src_device'], link['dst_device'] = link['dst_device'], link['src_device']
                            link['src_interface'], link['dst_interface'] = link['dst_interface'], link['src_interface']
                            # Safely swap descriptions without creating keys when absent
                            p1_desc = link['profile'].pop('peer1_description', None)
                            p2_desc = link['profile'].pop('peer2_description', None)
                            if p2_desc is not None:
                                link['profile']['peer1_description'] = p2_desc
                            if p1_desc is not None:
                                link['profile']['peer2_description'] = p1_desc
                            # Safely swap freeform without creating keys when absent
                            p1_free = link['profile'].pop('peer1_freeform', None)
                            p2_free = link['profile'].pop('peer2_freeform', None)
                            if p2_free is not None:
                                link['profile']['peer1_freeform'] = p2_free
                            if p1_free is not None:
                                link['profile']['peer2_freeform'] = p1_free

                        if 'templateName' not in existing_link:
                            not_required_links.append(link)
                        elif existing_link['templateName'] == 'int_pre_provision_intra_fabric_link':
                            required_links.append(link)
                        elif existing_link['templateName'] == 'int_intra_fabric_num_link':
                            # Populate additional fields from existing link
                            # into the required link. IPs are assigned by ND and not managed in NaC Fabric link
                            # at this time.
                            # When template is defined as int_pre_provision_intra_fabric_link, template is converted
                            # by ND to int_intra_fabric_num_link, when fabric-link is P2P and IPs are assigned.
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
    
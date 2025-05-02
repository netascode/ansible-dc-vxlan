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
    looking to remove from the fabric. If the link is not required, it will be
    added to links_to_be_removed list.
    """
    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        existing_links = self._task.args['existing_links']
        fabric_links = self._task.args['fabric_links']

        required_links = []
        links_to_be_removed = []
        filtered_existing_links = []
        for existing_link in existing_links:
            # Cannot assume the existing_link has the 'templateName' key so use get for safety
            if existing_link.get('templateName') == "int_pre_provision_intra_fabric_link" or existing_link.get('templateName') == "int_intra_fabric_num_link":
                filtered_existing_links.append(existing_link)
                for link in fabric_links:
                    if ('sw1-info' in existing_link and 'sw2-info' in existing_link and
                        'sw-sys-name' in existing_link['sw1-info'] and 'sw-sys-name' in existing_link['sw2-info'] and
                        (existing_link['sw1-info']['sw-sys-name'].lower() == link['src_device'].lower() and
                        existing_link['sw1-info']['if-name'].lower() == link['src_interface'].lower() and
                        existing_link['sw2-info']['sw-sys-name'].lower() == link['dst_device'].lower() and
                        existing_link['sw2-info']['if-name'].lower() == link['dst_interface'].lower()) or
                        (existing_link['sw1-info']['sw-sys-name'].lower() == link['dst_device'].lower() and
                        existing_link['sw1-info']['if-name'].lower() == link['dst_interface'].lower() and
                        existing_link['sw2-info']['sw-sys-name'].lower() == link['src_device'].lower() and
                        existing_link['sw2-info']['if-name'].lower() == link['src_interface'].lower())):
                        required_links.append(existing_link)
        for link in filtered_existing_links:
            link_found = False
            for required_link in required_links:
                if link == required_link:
                    link_found = True
                    break
            if not link_found:
                # The theory here is that links without a fabricName are links that are
                # automatically created by the system and should not be removed.
                #
                # TODO: This is a guess and should be confirmed.
                if link.get('fabricName') is None:
                    continue
                links_to_be_removed.append({
                    'dst_fabric': link['fabricName'],
                    'src_device': link['sw1-info']['sw-sys-name'],
                    'src_interface': link['sw1-info']['if-name'],
                    'dst_device': link['sw2-info']['sw-sys-name'],
                    'dst_interface': link['sw2-info']['if-name']
                })

        results['links_to_be_removed'] = links_to_be_removed
        return results

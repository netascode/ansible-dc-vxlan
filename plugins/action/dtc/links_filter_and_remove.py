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

from ansible.errors import AnsibleActionFail
from ansible.utils.display import Display
from ansible.plugins.action import ActionBase
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import (
    FABRIC_LINK_TEMPLATE_NUM,
    FABRIC_LINK_TEMPLATE_PRE_PROVISION,
    fabric_link_endpoints,
    link_endpoint_key,
    resolve_link_endpoints,
    switch_mgmt_ip_map,
)

display = Display()

ARGUMENT_SPEC = dict(
    existing_links=dict(type='list', elements='dict', required=True),
    fabric_links=dict(type='list', elements='dict', required=True),
    switch_data_model=dict(type='list', elements='dict', required=True),
)

REMOVABLE_TEMPLATES = (FABRIC_LINK_TEMPLATE_PRE_PROVISION, FABRIC_LINK_TEMPLATE_NUM)


class ActionModule(ActionBase):
    """
    This class is used to compare the existing links with the links that you are
    looking to remove from the fabric. If the link is not required, it will be
    added to links_to_be_removed list.
    """
    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['changed'] = False

        try:
            # Also rejects a null fabric_links, which would otherwise mark every link for removal.
            _validation, args = self.validate_argument_spec(argument_spec=ARGUMENT_SPEC)
        except AnsibleActionFail as error:
            results.update(failed=True, msg=f"links_filter_and_remove: {error.message}")
            return results

        ip_map = switch_mgmt_ip_map(args['switch_data_model'])
        known_devices = {str(ip).lower() for ip in ip_map.values()}
        managed_link_keys = {
            link_endpoint_key(*fabric_link_endpoints(link)) for link in args['fabric_links']
        }
        links_to_be_removed = []

        for existing_link in args['existing_links']:
            if existing_link.get('templateName') not in REMOVABLE_TEMPLATES:
                continue

            endpoints = resolve_link_endpoints(existing_link, ip_map)
            if endpoints is None:
                display.vvv("links_filter_and_remove: skipping controller link with incomplete sw1-info/sw2-info")
                continue
            if link_endpoint_key(*endpoints) in managed_link_keys:
                continue

            # The theory here is that links without a fabricName are links that are
            # automatically created by the system and should not be removed.
            #
            # TODO: This is a guess and should be confirmed.
            if existing_link.get('fabricName') is None:
                continue

            (src_device, src_interface), (dst_device, dst_interface) = endpoints
            unknown_devices = [device for device in (src_device, dst_device) if str(device).lower() not in known_devices]
            if unknown_devices:
                display.warning(
                    f"links_filter_and_remove: not removing link {src_device}:{src_interface} -> "
                    f"{dst_device}:{dst_interface}; device(s) {', '.join(map(str, unknown_devices))} "
                    f"not found in the switch data model"
                )
                continue

            links_to_be_removed.append({
                'dst_fabric': existing_link['fabricName'],
                'src_device': src_device,
                'src_interface': src_interface,
                'dst_device': dst_device,
                'dst_interface': dst_interface,
            })

        results['links_to_be_removed'] = links_to_be_removed
        return results

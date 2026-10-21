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
    FABRIC_LINK_TEMPLATE_UNNUM,
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


class ActionModule(ActionBase):
    """
    This class is used to compare the existing links with the links that you are
    looking to add to the fabric. If the link already exists, it will be added to
    the not_required_links list.
    """

    # Profile field -> nvPairs key mapping for value-level comparison
    PROFILE_TO_NV = {
        'admin_state': 'ADMIN_STATE',
        'mtu': 'MTU',
        'peer1_description': 'PEER1_DESC',
        'peer2_description': 'PEER2_DESC',
        'peer1_cmds': 'PEER1_CONF',
        'peer2_cmds': 'PEER2_CONF',
        'peer1_ipv4_addr': 'PEER1_IP',
        'peer2_ipv4_addr': 'PEER2_IP',
        'enable_macsec': 'ENABLE_MACSEC',
    }

    # Optional/conditional fields that may be absent from desired profile
    # but present on controller (field removal detection)
    REMOVAL_KEYS = {
        'peer1_cmds': 'PEER1_CONF',
        'peer2_cmds': 'PEER2_CONF',
    }

    # peer1_<suffix>/peer2_<suffix> profile keys that follow their endpoint when a link is reversed
    SWAP_SUFFIXES = ('description', 'cmds', 'ipv4_addr')

    def _link_profile_changed(self, link, existing_link):
        """
        Compare enriched link profile against controller nvPairs.

        Returns True if any profile value differs from the controller,
        or if the controller has non-empty values for fields absent
        from the desired profile (field removal detection).
        """
        nv = existing_link.get('nvPairs') or {}
        profile = link.get('profile') or {}
        src = link.get('src_device', '')
        src_if = link.get('src_interface', '')
        dst = link.get('dst_device', '')
        dst_if = link.get('dst_interface', '')

        # Forward check: desired profile keys differ from controller
        for pkey, nv_key in self.PROFILE_TO_NV.items():
            if pkey in profile:
                desired_val = str(profile[pkey]).strip()
                ctrl_val = str(nv.get(nv_key, '')).strip()
                if desired_val.lower() != ctrl_val.lower():
                    display.vvv(
                        f"existing_links_check: DIFF [{src}:{src_if}->{dst}:{dst_if}]: "
                        f"{pkey}={desired_val!r} vs {nv_key}={ctrl_val!r}"
                    )
                    return True

        # Reverse check: controller has non-empty values for keys
        # absent from desired profile (field was removed by user)
        for pkey, nv_key in self.REMOVAL_KEYS.items():
            if pkey not in profile:
                ctrl_val = str(nv.get(nv_key, '')).strip()
                if ctrl_val:
                    display.vvv(
                        f"existing_links_check: DIFF [{src}:{src_if}->{dst}:{dst_if}]: "
                        f"{nv_key}={ctrl_val!r} on controller but "
                        f"{pkey} absent from desired profile (removed)"
                    )
                    return True

        display.vvv(
            f"existing_links_check: NO DIFF [{src}:{src_if}->{dst}:{dst_if}]: "
            f"profile matches controller"
        )
        return False

    @staticmethod
    def _index_existing_links(existing_links, ip_map):
        """Map direction-independent endpoint keys to (existing_link, endpoints); first entry wins."""
        index = {}
        for existing_link in existing_links:
            endpoints = resolve_link_endpoints(existing_link, ip_map)
            if endpoints is None:
                display.vvv("existing_links_check: ignoring controller link with incomplete sw1-info/sw2-info")
                continue
            key = link_endpoint_key(*endpoints)
            if key in index:
                display.vvv(f"existing_links_check: ignoring duplicate controller link {endpoints}")
                continue
            index[key] = (existing_link, endpoints)
        return index

    def _align_direction(self, link, sw1_endpoint):
        """Swap src/dst and peer-specific profile fields when the controller lists the link reversed."""
        src = (str(link.get('src_device')).lower(), str(link.get('src_interface')).lower())
        if src == tuple(str(value).lower() for value in sw1_endpoint):
            return
        link['src_device'], link['dst_device'] = link.get('dst_device'), link.get('src_device')
        link['src_interface'], link['dst_interface'] = link.get('dst_interface'), link.get('src_interface')
        # Model IPv4 addresses follow their endpoint; numbered links overwrite them from the controller.
        profile = link['profile']
        for suffix in self.SWAP_SUFFIXES:
            peer1 = profile.pop(f'peer1_{suffix}', None)
            peer2 = profile.pop(f'peer2_{suffix}', None)
            if peer2 is not None:
                profile[f'peer1_{suffix}'] = peer2
            if peer1 is not None:
                profile[f'peer2_{suffix}'] = peer1

    def _is_required(self, link, existing_link):
        """Enrich link from the matching controller link and return True if it must be pushed."""
        template = existing_link.get('templateName')

        if template is None:
            # Discovered-only adjacency with no policy; the next run returns a real templateName.
            display.vvv("existing_links_check: → REQUIRED (templateName missing, configuring data-model link on discovered adjacency)")
            return True

        if template == FABRIC_LINK_TEMPLATE_PRE_PROVISION:
            display.vvv("existing_links_check: → REQUIRED (pre-provision)")
            return True

        if template == FABRIC_LINK_TEMPLATE_NUM:
            # ND converts pre-provision links to num_link once IPs are assigned; IPs stay ND-managed.
            nv = existing_link.get('nvPairs') or {}
            profile = link['profile']
            link['template'] = FABRIC_LINK_TEMPLATE_NUM
            if 'PEER1_IP' in nv:
                profile['peer1_ipv4_addr'] = nv['PEER1_IP']
            if 'PEER2_IP' in nv:
                profile['peer2_ipv4_addr'] = nv['PEER2_IP']
            profile['enable_macsec'] = nv.get('ENABLE_MACSEC') or 'false'
            label = 'num_link, enriched'
        elif template == FABRIC_LINK_TEMPLATE_UNNUM:
            link['template'] = FABRIC_LINK_TEMPLATE_UNNUM
            label = 'unnum_link'
        else:
            display.warning(
                f"existing_links_check: skipping link "
                f"{link.get('src_device')}:{link.get('src_interface')} -> "
                f"{link.get('dst_device')}:{link.get('dst_interface')}; "
                f"controller templateName '{template}' is not managed by this collection"
            )
            return False

        if self._link_profile_changed(link, existing_link):
            display.vvv(f"existing_links_check: → REQUIRED ({label}, profile changed)")
            return True
        display.vvv(f"existing_links_check: → NOT REQUIRED ({label}, profile matches)")
        return False

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['changed'] = False

        try:
            _validation, args = self.validate_argument_spec(argument_spec=ARGUMENT_SPEC)
        except AnsibleActionFail as error:
            results.update(failed=True, msg=f"existing_links_check: {error.message}")
            return results

        ip_map = switch_mgmt_ip_map(args['switch_data_model'])
        existing_index = self._index_existing_links(args['existing_links'], ip_map)
        required_links = []
        not_required_links = []
        display.vvv(
            f"existing_links_check: {len(args['fabric_links'])} configured links, "
            f"{len(args['existing_links'])} existing links from NDFC"
        )

        for fabric_link in args['fabric_links']:
            link = dict(fabric_link, profile=dict(fabric_link.get('profile') or {}))
            display.vvv(
                f"existing_links_check: evaluating configured link "
                f"src={link.get('src_device')}:{link.get('src_interface')} → "
                f"dst={link.get('dst_device')}:{link.get('dst_interface')} "
                f"template={link.get('template')}"
            )

            match = existing_index.get(link_endpoint_key(*fabric_link_endpoints(link)))
            if match is None:
                display.vvv("existing_links_check: → REQUIRED (no existing match, new link)")
                required_links.append(link)
                continue

            existing_link, (sw1_endpoint, sw2_endpoint) = match
            display.vvv(
                f"existing_links_check: MATCH found — "
                f"existing sw1={sw1_endpoint[0]}:{sw1_endpoint[1]} "
                f"sw2={sw2_endpoint[0]}:{sw2_endpoint[1]} "
                f"templateName={existing_link.get('templateName', '<missing>')}"
            )
            self._align_direction(link, sw1_endpoint)

            if self._is_required(link, existing_link):
                required_links.append(link)
            else:
                not_required_links.append(link)

        display.vvv(
            f"existing_links_check: RESULT — "
            f"required={len(required_links)}, not_required={len(not_required_links)}"
        )
        results['required_links'] = required_links
        return results

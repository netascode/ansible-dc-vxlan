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

# This is an example file for help functions that can be called by
# our various action plugins for common routines.
#
# For example in prepare_serice_model.py we can do the following:
#  from ..helper_functions import do_something

root_key = 'vxlan'
# Keys here match data model schema
# type: enum('VXLAN_EVPN', 'MSD', 'MCF', 'ISN')
model_keys = {'VXLAN_EVPN': {}, 'MSD': {}, 'MFD': {}, 'ISN': {}}


# VXLAN_EVPN KEYS

model_keys['VXLAN_EVPN']['global'] = [root_key, 'global', 'KEY']
model_keys['VXLAN_EVPN']['global.dns_servers'] = [root_key, 'global', 'dns_servers', 'LIST']
model_keys['VXLAN_EVPN']['global.ntp_servers'] = [root_key, 'global', 'ntp_servers', 'LIST']
model_keys['VXLAN_EVPN']['global.syslog_servers'] = [root_key, 'global', 'syslog_servers', 'LIST']
model_keys['VXLAN_EVPN']['global.netflow'] = [root_key, 'global', 'netflow', 'KEY']
model_keys['VXLAN_EVPN']['global.netflow.exporter'] = [root_key, 'global', 'netflow', 'exporter', 'LIST']
model_keys['VXLAN_EVPN']['global.netflow.record'] = [root_key, 'global', 'netflow', 'record', 'LIST']
model_keys['VXLAN_EVPN']['global.netflow.monitor'] = [root_key, 'global', 'netflow', 'monitor', 'LIST']
model_keys['VXLAN_EVPN']['global.spanning_tree'] = [root_key, 'global', 'spanning_tree', 'KEY']
# ---
model_keys['VXLAN_EVPN']['underlay'] = [root_key, 'underlay', 'KEY']
# ---
model_keys['VXLAN_EVPN']['topology'] = [root_key, 'topology', 'KEY']
model_keys['VXLAN_EVPN']['topology.edge_connections'] = [root_key, 'topology', 'edge_connections', 'LIST']
model_keys['VXLAN_EVPN']['topology.fabric_links'] = [root_key, 'topology', 'fabric_links', 'LIST']
model_keys['VXLAN_EVPN']['topology.switches'] = [root_key, 'topology', 'switches', 'LIST']
model_keys['VXLAN_EVPN']['topology.switches.freeform'] = [root_key, 'topology', 'switches', 'freeform', 'LIST_INDEX']
model_keys['VXLAN_EVPN']['topology.switches.interfaces'] = [root_key, 'topology', 'switches', 'interfaces', 'LIST_INDEX']
model_keys['VXLAN_EVPN']['topology.vpc_peers'] = [root_key, 'topology', 'vpc_peers', 'LIST']
# ---
model_keys['VXLAN_EVPN']['overlay'] = [root_key, 'overlay', 'KEY']
model_keys['VXLAN_EVPN']['overlay.vrfs'] = [root_key, 'overlay', 'vrfs', 'LIST']
model_keys['VXLAN_EVPN']['overlay.vrf_attach_groups'] = [root_key, 'overlay', 'vrf_attach_groups', 'LIST']
model_keys['VXLAN_EVPN']['overlay.vrf_attach_groups.switches'] = [root_key, 'overlay', 'vrf_attach_groups', 'switches', 'LIST_INDEX']
model_keys['VXLAN_EVPN']['overlay.networks'] = [root_key, 'overlay', 'networks', 'LIST']
model_keys['VXLAN_EVPN']['overlay.network_attach_groups'] = [root_key, 'overlay', 'network_attach_groups', 'LIST']
model_keys['VXLAN_EVPN']['overlay.network_attach_groups.switches'] = [root_key, 'overlay', 'network_attach_groups', 'switches', 'LIST_INDEX']
# ---
model_keys['VXLAN_EVPN']['overlay_extensions'] = [root_key, 'overlay_extensions', 'KEY']
model_keys['VXLAN_EVPN']['overlay_extensions.route_control'] = [root_key, 'overlay_extensions', 'route_control', 'KEY']
model_keys['VXLAN_EVPN']['overlay_extensions.route_control.route_maps'] = [root_key, 'overlay_extensions', 'route_control', 'route_maps', 'LIST']
# ---
model_keys['VXLAN_EVPN']['policy'] = [root_key, 'policy', 'KEY']
model_keys['VXLAN_EVPN']['policy.policies'] = [root_key, 'policy', 'policies', 'LIST']
model_keys['VXLAN_EVPN']['policy.groups'] = [root_key, 'policy', 'groups', 'LIST']
model_keys['VXLAN_EVPN']['policy.switches'] = [root_key, 'policy', 'switches', 'LIST']

# ISN KEYS

model_keys['ISN']['topology'] = [root_key, 'topology', 'KEY']
model_keys['ISN']['topology.edge_connections'] = [root_key, 'topology', 'edge_connections', 'LIST']
model_keys['ISN']['topology.fabric_links'] = [root_key, 'topology', 'fabric_links', 'LIST']
model_keys['ISN']['topology.switches'] = [root_key, 'topology', 'switches', 'LIST']
model_keys['ISN']['topology.switches.freeform'] = [root_key, 'topology', 'switches', 'freeform', 'LIST_INDEX']
model_keys['ISN']['topology.switches.interfaces'] = [root_key, 'topology', 'switches', 'interfaces', 'LIST_INDEX']
model_keys['ISN']['topology.vpc_peers'] = [root_key, 'topology', 'vpc_peers', 'LIST']
# ---
model_keys['ISN']['policy'] = [root_key, 'policy', 'KEY']
model_keys['ISN']['policy.policies'] = [root_key, 'policy', 'policies', 'LIST']
model_keys['ISN']['policy.groups'] = [root_key, 'policy', 'groups', 'LIST']
model_keys['ISN']['policy.switches'] = [root_key, 'policy', 'switches', 'LIST']

# MSD KEYS

# ---
model_keys['MSD']['multisite'] = [root_key, 'multisite', 'KEY']
model_keys['MSD']['multisite.child_fabrics'] = [root_key, 'multisite', 'child_fabrics', 'KEY']
model_keys['MSD']['multisite.overlay'] = [root_key, 'multisite', 'overlay', 'KEY']
model_keys['MSD']['multisite.overlay.vrfs'] = [root_key, 'multisite', 'overlay', 'vrfs', 'LIST']
model_keys['MSD']['multisite.overlay.vrf_attach_groups'] = [root_key, 'multisite', 'overlay', 'vrf_attach_groups', 'LIST']
model_keys['MSD']['multisite.overlay.vrf_attach_groups.switches'] = [root_key, 'multisite', 'overlay', 'vrf_attach_groups', 'switches', 'LIST_INDEX']
model_keys['MSD']['multisite.overlay.networks'] = [root_key, 'multisite', 'overlay', 'networks', 'LIST']
model_keys['MSD']['multisite.overlay.network_attach_groups'] = [root_key, 'multisite', 'overlay', 'network_attach_groups', 'LIST']
model_keys['MSD']['multisite.overlay.network_attach_groups.switches'] = [root_key, 'multisite', 'overlay', 'network_attach_groups', 'switches', 'LIST_INDEX']

# MFD KEYS

# ---
model_keys['MFD']['multisite'] = [root_key, 'multisite', 'KEY']
model_keys['MFD']['multisite.child_fabrics'] = [root_key, 'multisite', 'child_fabrics', 'KEY']
model_keys['MFD']['multisite.overlay'] = [root_key, 'multisite', 'overlay', 'KEY']
model_keys['MFD']['multisite.overlay.vrfs'] = [root_key, 'multisite', 'overlay', 'vrfs', 'LIST']
model_keys['MFD']['multisite.overlay.vrf_attach_groups'] = [root_key, 'multisite', 'overlay', 'vrf_attach_groups', 'LIST']
model_keys['MFD']['multisite.overlay.vrf_attach_groups.switches'] = [root_key, 'multisite', 'overlay', 'vrf_attach_groups', 'switches', 'LIST_INDEX']
model_keys['MFD']['multisite.overlay.networks'] = [root_key, 'multisite', 'overlay', 'networks', 'LIST']
model_keys['MFD']['multisite.overlay.network_attach_groups'] = [root_key, 'multisite', 'overlay', 'network_attach_groups', 'LIST']
model_keys['MFD']['multisite.overlay.network_attach_groups.switches'] = [root_key, 'multisite', 'overlay', 'network_attach_groups', 'switches', 'LIST_INDEX']


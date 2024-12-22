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

model_keys = {}
model_keys['fabric.name'] = [root_key, 'fabric', 'name', 'KEY']
model_keys['fabric.type'] = [root_key, 'fabric', 'type', 'KEY']

model_keys['global'] = [root_key, 'global', 'KEY']
model_keys['global.dns_servers'] = [root_key, 'global', 'dns_servers', 'LIST']
model_keys['global.ntp_servers'] = [root_key, 'global', 'ntp_servers', 'LIST']
model_keys['global.syslog_servers'] = [root_key, 'global', 'syslog_servers', 'LIST']
model_keys['global.netflow'] = [root_key, 'global', 'netflow', 'KEY']
model_keys['global.netflow.exporter'] = [root_key, 'global', 'netflow', 'exporter', 'LIST']
model_keys['global.netflow.record'] = [root_key, 'global', 'netflow', 'record', 'LIST']
model_keys['global.netflow.monitor'] = [root_key, 'global', 'netflow', 'monitor', 'LIST']
model_keys['global.spanning_tree'] = [root_key, 'global', 'spanning_tree', 'KEY']
model_keys['global.spanning_tree.vlan_range'] = [root_key, 'global', 'spanning_tree', 'vlan_range', 'LIST']
model_keys['global.spanning_tree.mst_instance_range'] = [root_key, 'global', 'spanning_tree', 'mst_instance_range', 'LIST']
# ---
model_keys['underlay'] = [root_key, 'underlay', 'KEY']
# ---
model_keys['topology'] = [root_key, 'topology', 'KEY']
model_keys['topology.edge_connections'] = [root_key, 'topology', 'edge_connections', 'LIST']
model_keys['topology.fabric_links'] = [root_key, 'topology', 'fabric_links', 'LIST']
model_keys['topology.switches'] = [root_key, 'topology', 'switches', 'LIST']
model_keys['topology.vpc_peers'] = [root_key, 'topology', 'vpc_peers', 'LIST']
# ---
model_keys['overlay'] = [root_key, 'overlay', 'KEY']
model_keys['overlay.vrfs'] = [root_key, 'overlay', 'vrfs', 'LIST']
model_keys['overlay.vrf_attach_groups'] = [root_key, 'overlay', 'vrf_attach_groups', 'LIST']
model_keys['overlay.networks'] = [root_key, 'overlay', 'networks', 'LIST']
model_keys['overlay.network_attach_groups'] = [root_key, 'overlay', 'network_attach_groups', 'LIST']
# ---
model_keys['multisite'] = [root_key, 'multisite', 'KEY']
model_keys['multisite.overlay'] = [root_key, 'multisite', 'overlay', 'KEY']
model_keys['multisite.overlay.vrfs'] = [root_key, 'multisite', 'overlay', 'vrfs', 'LIST']
model_keys['multisite.overlay.vrf_attach_groups'] = [root_key, 'multisite', 'overlay', 'vrf_attach_groups', 'LIST']
model_keys['multisite.overlay.networks'] = [root_key, 'multisite', 'overlay', 'networks', 'LIST']
model_keys['multisite.overlay.network_attach_groups'] = [root_key, 'multisite', 'overlay', 'network_attach_groups', 'LIST']
# ---
model_keys['policy'] = [root_key, 'policy', 'KEY']
model_keys['policy.policies'] = [root_key, 'policy', 'policies', 'LIST']
model_keys['policy.groups'] = [root_key, 'policy', 'groups', 'LIST']
model_keys['policy.switches'] = [root_key, 'policy', 'switches', 'LIST']

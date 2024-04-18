# Group vPC interfaces by vpc_peers, vpc_id and switch_name
# This helps in identifying vPC interfaces for a given vpc_peer, vpc_id and switch_name
# Reduces the need to loop through all interfaces to find vPC interfaces in Jinja2 templates
class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        model_data = self.kwargs['results']['model_extended']
        # Check if fabric.topology is defined
        if model_data.get('fabric').get('topology') is not None:
            model_data['fabric']['topology'] = model_data.get('fabric').get('topology', {})
            # Check if fabric.topology.switches is defined
            if model_data.get('fabric').get('topology').get('switches') is not None:
                # Initialize fabric.topology.interfaces.vpc_interfaces
                model_data['fabric']['topology']['interfaces'] = model_data.get('fabric').get('topology').get('interfaces', {})
                model_data['fabric']['topology']['interfaces']['vpc_interfaces'] = \
                    model_data.get('fabric').get('topology').get('interfaces').get('vpc_interfaces', {})
                # if fabric.topology.vpc_peers is defined
                if model_data.get('fabric').get('topology').get('vpc_peers') is not None:
                    # Loop through each vpc_peers
                    for vpc_peer in model_data.get('fabric').get('topology').get('vpc_peers'):
                        # Loop through each switch
                        for switch in model_data.get('fabric').get('topology').get('switches'):
                            # Check if switch name is part of vpc_peer
                            if switch.get('name') == vpc_peer.get('peer1') or switch.get('name') == vpc_peer.get('peer2'):
                                # Check if switch has interfaces
                                if switch.get('interfaces') is not None:
                                    # Loop through each interface
                                    for interface in switch.get('interfaces'):
                                        # Check if interface has vpc_id
                                        if interface.get('vpc_id') is not None:
                                            # Initialize fabric.topology.interfaces.vpc_interfaces.<peer1>___<peer2>.<vpc_id>.<switch_name>
                                            model_data['fabric']['topology']['interfaces']['vpc_interfaces'][vpc_peer.get('peer1') + "___" + vpc_peer.get('peer2')] = model_data['fabric']['topology']['interfaces']['vpc_interfaces'].get(vpc_peer.get('peer1') + "___" + vpc_peer.get('peer2'), {})  # noqa: E501
                                            model_data['fabric']['topology']['interfaces']['vpc_interfaces'][vpc_peer.get('peer1') + "___" + vpc_peer.get('peer2')][interface.get('vpc_id')] = model_data['fabric']['topology']['interfaces']['vpc_interfaces'][vpc_peer.get('peer1') + "___" + vpc_peer.get('peer2')].get(interface.get('vpc_id'), {})  # noqa: E501
                                            model_data['fabric']['topology']['interfaces']['vpc_interfaces'][vpc_peer.get('peer1') + "___" + vpc_peer.get('peer2')][interface.get('vpc_id')][switch.get('name')] = model_data['fabric']['topology']['interfaces']['vpc_interfaces'][vpc_peer.get('peer1') + "___" + vpc_peer.get('peer2')][interface.get('vpc_id')].get(switch.get('name'), {})  # noqa: E501
                                            # Assign interface to fabric.topology.interfaces.vpc_interfaces.<peer1>___<peer2>.<vpc_id>.<switch_name>
                                            model_data['fabric']['topology']['interfaces']['vpc_interfaces'][vpc_peer.get('peer1') + "___" + vpc_peer.get('peer2')][interface.get('vpc_id')][switch.get('name')] = interface  # noqa: E501
        # Update model_extended with updated model_data
        self.kwargs['results']['model_extended'] = model_data
        return self.kwargs['results']

# ========================================================
# Sample Input
# ========================================================
# fabric:
#   topology:
#     vpc_peers:
#       - peer1: dc1-leaf1
#         peer2: dc1-leaf2
#         domain_id: 10
#         vtep_vip: "10.10.88.1"
#     switches:
#       - name: dc1-leaf1
#         role: leaf
#         interfaces:
#           - name: port-channel1
#             mode: access
#             description: 'topology_switch_access_po_interface'
#             vpc_id: 3
#             mtu: jumbo
#             speed: auto
#             enabled: True
#             spanning_tree_portfast: True
#             pc_mode: active
#             members:
#               - eth1/16
#               - eth1/17
#       - name: dc1-leaf2
#         role: leaf
#         interfaces:
#           - name: port-channel1
#             mode: access
#             description: 'topology_switch_access_po_interface1'
#             vpc_id: 3
#             mtu: jumbo
#             speed: auto
#             enabled: True
#             spanning_tree_portfast: True
#             pc_mode: active
#             members:
#               - eth1/16
#               - eth1/17
# ========================================================
# Sample Outout (MD_Extended)
# ========================================================
# {
#     "fabric": {
#         "topology": {
#             "interfaces": {
#                 "vpc_interfaces": {
#                     "dc1-leaf1___dc1-leaf2": {
#                         "3": {
#                             "dc1-leaf1": {
#                                 "description": "topology_switch_access_po_interface",
#                                 "enabled": true,
#                                 "members": [
#                                     "eth1/16",
#                                     "eth1/17"
#                                 ],
#                                 "mode": "access",
#                                 "mtu": "jumbo",
#                                 "name": "port-channel1",
#                                 "pc_mode": "active",
#                                 "spanning_tree_portfast": true,
#                                 "speed": "auto",
#                                 "vpc_id": 3
#                             },
#                             "dc1-leaf2": {
#                                 "description": "topology_switch_access_po_interface1",
#                                 "enabled": true,
#                                 "members": [
#                                     "eth1/16",
#                                     "eth1/17"
#                                 ],
#                                 "mode": "access",
#                                 "mtu": "jumbo",
#                                 "name": "port-channel1",
#                                 "pc_mode": "active",
#                                 "spanning_tree_portfast": true,
#                                 "speed": "auto",
#                                 "vpc_id": 3
#                             }
#                         }
#                     }
#                 }
#             }
#         }
#     }
# }
# ========================================================

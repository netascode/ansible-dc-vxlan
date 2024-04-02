## Group vPC interfaces by vpc_peers, vpc_id and switch_name
##
class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = ['fabric', 'topology', 'switches', 'interfaces', 'vpc_peers']

    def prepare(self):
        model_data = self.kwargs['results']['model_extended']
        if model_data.get(self.keys[0]).get(self.keys[1]) is not None:
            model_data['fabric']['topology'] = model_data.get('fabric').get('topology', {})
            if model_data.get(self.keys[0]).get(self.keys[1]).get(self.keys[2]) is not None:
                model_data['fabric']['topology']['interfaces'] = model_data.get('fabric').get('topology').get('interfaces', {})
                model_data['fabric']['topology']['interfaces']['vpc_interfaces'] = model_data.get('fabric').get('topology').get('interfaces').get('vpc_interfaces', {})
                if model_data.get(self.keys[0]).get(self.keys[1]).get(self.keys[4]) is not None:
                    for vpc_peer in model_data.get(self.keys[0]).get(self.keys[1]).get(self.keys[4]):
                        if model_data.get(self.keys[0]).get(self.keys[1]).get(self.keys[2]) is not None:
                            for switch in model_data.get(self.keys[0]).get(self.keys[1]).get(self.keys[2]):
                                if switch.get('name') == vpc_peer.get('peer1') or switch.get('name') == vpc_peer.get('peer2'):
                                    if switch.get(self.keys[3]) is not None:
                                        for interface in switch.get(self.keys[3]):
                                            if interface.get('vpc_id') is not None:
                                                model_data['fabric']['topology']['interfaces']['vpc_interfaces'][vpc_peer.get('peer1')+"___"+vpc_peer.get('peer2')] = model_data['fabric']['topology']['interfaces']['vpc_interfaces'].get(vpc_peer.get('peer1')+"___"+vpc_peer.get('peer2'), {})
                                                model_data['fabric']['topology']['interfaces']['vpc_interfaces'][vpc_peer.get('peer1')+"___"+vpc_peer.get('peer2')][interface.get('vpc_id')] = model_data['fabric']['topology']['interfaces']['vpc_interfaces'][vpc_peer.get('peer1')+"___"+vpc_peer.get('peer2')].get(interface.get('vpc_id'), {})
                                                model_data['fabric']['topology']['interfaces']['vpc_interfaces'][vpc_peer.get('peer1')+"___"+vpc_peer.get('peer2')][interface.get('vpc_id')][switch.get('name')] = model_data['fabric']['topology']['interfaces']['vpc_interfaces'][vpc_peer.get('peer1')+"___"+vpc_peer.get('peer2')][interface.get('vpc_id')].get(switch.get('name'), {})
                                                model_data['fabric']['topology']['interfaces']['vpc_interfaces'][vpc_peer.get('peer1')+"___"+vpc_peer.get('peer2')][interface.get('vpc_id')][switch.get('name')] = interface
        self.kwargs['results']['model_extended'] = model_data
        return self.kwargs['results']
    
## Sample output

# "vpc_interfaces": {
#     "dc1-leaf1___dc1-leaf2": {
#         "3": {
#             "dc1-leaf1": {
#                 "description": "topology_switch_access_po_interface",
#                 "enabled": true,
#                 "members": [
#                     "eth1/16",
#                     "eth1/17"
#                 ],
#                 "mode": "access",
#                 "mtu": "jumbo",
#                 "name": "port-channel1",
#                 "pc_mode": "active",
#                 "spanning_tree_portfast": true,
#                 "speed": "auto",
#                 "vpc_id": 3
#             },
#             "dc1-leaf2": {
#                 "description": "topology_switch_access_po_interface",
#                 "enabled": true,
#                 "members": [
#                     "eth1/16",
#                     "eth1/17"
#                 ],
#                 "mode": "access",
#                 "mtu": "jumbo",
#                 "name": "port-channel1",
#                 "pc_mode": "active",
#                 "spanning_tree_portfast": true,
#                 "speed": "auto",
#                 "vpc_id": 3
#             }
#         }
#     },
# }

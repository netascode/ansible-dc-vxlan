## Count interfaces of different types and expose in extended service model for controls within playbooks
##
class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = ['fabric', 'topology', 'switches', 'interfaces']
        # interface modes which are a direct match
        self.mode_direct = ['routed', 'routed_po', 'routed_sub', 'loopback', 'fabric_loopback', 'mpls_loopback']
        # interface modes which need additional validation
        self.mode_indirect = ['access', 'trunk', 'access_po', 'trunk_po', 'access_vpc', 'trunk_vpc', 'all']

    def prepare(self):
        model_data = self.kwargs['results']['model_extended']
        model_data[self.keys[0]][self.keys[1]][self.keys[3]] = {}
        model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes'] = {}
        # loop through interface modes and initialize with interface count 0
        for mode in self.mode_direct:
            model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes'][mode] = {}
            model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes'][mode]['count'] = 0
        for mode in self.mode_indirect:
            model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes'][mode] = {}
            model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes'][mode]['count'] = 0
        if not model_data.get(self.keys[0], None):
            if not model_data.get(self.keys[0]).get(self.keys[1], None):
                if not model_data.get(self.keys[0]).get(self.keys[1]).get(self.keys[2], None):
                    # loop through switches
                    for switch in model_data.get(self.keys[0]).get(self.keys[1]).get(self.keys[2]):
                        # if switch has interfaces
                        if switch.get(self.keys[3]) is not None:
                            # loop through interfaces
                            for interface in switch.get(self.keys[3]):
                                # loop through interface modes direct and count
                                for interface_mode in self.mode_direct:
                                    # if interface mode is a direct match, then increment the count for that mode
                                    if interface_mode == interface.get('mode'):
                                        model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes'][interface_mode]['count'] +=1
                                        model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes']['all']['count'] +=1
                                # loop through interface modes indirect along with additional validation and count
                                if interface.get('mode') == 'access':
                                    # if interface name starts with 'po' and has vpc_id, then it is a vpc access interface
                                    if interface.get('name').lower().startswith('po') and interface.get('vpc_id'):
                                        model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes']['access_vpc']['count'] +=1
                                        model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes']['all']['count'] +=1
                                    # if interface name starts with 'po', then it is a port-channel access interface
                                    elif interface.get('name').lower().startswith('po'):
                                        model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes']['access_po']['count'] +=1
                                        model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes']['all']['count'] +=1
                                    # else it is a regular access interface
                                    else:
                                        model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes']['access']['count'] +=1
                                        model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes']['all']['count'] +=1
                                if interface.get('mode') == 'trunk':
                                    # if interface name starts with 'po' and has vpc_id, then it is a vpc trunk interface
                                    if interface.get('name').lower().startswith('po') and interface.get('vpc_id'):
                                        model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes']['trunk_vpc']['count'] +=1
                                        model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes']['all']['count'] +=1
                                    # if interface name starts with 'po', then it is a port-channel trunk interface
                                    elif interface.get('name').lower().startswith('po'):
                                        model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes']['trunk_po']['count'] +=1
                                        model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes']['all']['count'] +=1
                                    # else it is a regular trunk interface
                                    else:
                                        model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes']['trunk']['count'] +=1
                                        model_data[self.keys[0]][self.keys[1]][self.keys[3]]['modes']['all']['count'] +=1

        self.kwargs['results']['model_extended'] = model_data
        return self.kwargs['results']
class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = ['fabric', 'overlay_services', 'vrfs', 'vrf_attach_groups', 'networks', 'network_attach_groups']

    def prepare(self):
        model_data = self.kwargs['results']['model_extended']

        # Handle VRFs/Networks Under Overlay Services.  Need to create an empty list
        # if vrfs/networks or vrf/networks key is not present in the service model data
        if not model_data.get(self.keys[0], None):
            if not model_data.get(self.keys[0]).get(self.keys[1], None):
                model_data[self.keys[0]][self.keys[1]] = {self.keys[2]: []}
                model_data[self.keys[0]][self.keys[1]] = {self.keys[4]: []}
            if not model_data.get(self.keys[0]).get(self.keys[1]).get(self.keys[2], None):
                model_data[self.keys[0]][self.keys[1]][self.keys[2]] = []
            if not model_data.get(self.keys[0]).get(self.keys[1]).get(self.keys[4], None):
                model_data[self.keys[0]][self.keys[1]][self.keys[4]] = []

        # Rebuild sm_data['fabric']['overlay_services']['vrf_attach_groups'] into
        # a structure that is easier to use.
        if model_data.get(self.keys[0], None):
            if model_data.get(self.keys[0]).get(self.keys[1], None):
                if model_data.get(self.keys[0]).get(self.keys[1]).get('vrf_attach_groups', None):
                    model_data[self.keys[0]][self.keys[1]]['vrf_attach_groups_dict'] = {}
                    for grp in model_data[self.keys[0]][self.keys[1]][self.keys[3]]:
                        model_data[self.keys[0]][self.keys[1]]['vrf_attach_groups_dict'][grp['name']] = []
                        for switch in grp['switches']:
                            model_data[self.keys[0]][self.keys[1]]['vrf_attach_groups_dict'][grp['name']].append(switch)

        # Rebuild sm_data['fabric']['overlay_services']['network_attach_groups'] into
        # a structure that is easier to use.
        if model_data.get(self.keys[0], None):
            if model_data.get(self.keys[0]).get(self.keys[1], None):
                if model_data.get(self.keys[0]).get(self.keys[1]).get('network_attach_groups', None):
                    model_data[self.keys[0]][self.keys[1]]['network_attach_groups_dict'] = {}
                    for grp in model_data[self.keys[0]][self.keys[1]][self.keys[5]]:
                        model_data[self.keys[0]][self.keys[1]]['network_attach_groups_dict'][grp['name']] = []
                        for switch in grp['switches']:
                            model_data[self.keys[0]][self.keys[1]]['network_attach_groups_dict'][grp['name']].append(switch)

        self.kwargs['results']['model_extended'] = model_data
        return self.kwargs['results']

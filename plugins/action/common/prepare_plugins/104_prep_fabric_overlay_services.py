class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = ['fabric', 'overlay_services', 'vrfs', 'networks']

    def prepare(self):
        model_data = self.kwargs['results']['model_extended']

        # Handle VRFs/Networks Under Overlay Services.  Need to create an empty list
        # if vrfs/networks or vrf/networks key is not present in the service model data
        if model_data.get('fabric').get('overlay_services') is None:
            model_data['fabric']['overlay_services'] = {'vrfs': []}
            model_data['fabric']['overlay_services'] = {'networks': []}
        if model_data.get('fabric').get('overlay_services').get('vrfs') is None:
            model_data['fabric']['overlay_services']['vrfs'] = []
        if model_data.get('fabric').get('overlay_services').get('networks') is None:
            model_data['fabric']['overlay_services']['networks'] = []

        # Rebuild sm_data['fabric']['overlay_services']['vrf_attach_groups'] into
        # a structure that is easier to use.
        model_data['fabric']['overlay_services']['vrf_attach_groups_dict'] = {}
        for grp in model_data['fabric']['overlay_services']['vrf_attach_groups']:
            model_data['fabric']['overlay_services']['vrf_attach_groups_dict'][grp['name']] = []
            for switch in grp['switches']:
                model_data['fabric']['overlay_services']['vrf_attach_groups_dict'][grp['name']].append(switch)

        # Rebuild sm_data['fabric']['overlay_services']['network_attach_groups'] into
        # a structure that is easier to use.
        model_data['fabric']['overlay_services']['network_attach_groups_dict'] = {}
        for grp in model_data['fabric']['overlay_services']['network_attach_groups']:
            model_data['fabric']['overlay_services']['network_attach_groups_dict'][grp['name']] = []
            for switch in grp['switches']:
                model_data['fabric']['overlay_services']['network_attach_groups_dict'][grp['name']].append(switch)

        self.kwargs['results']['model_extended'] = model_data
        return self.kwargs['results']

from ansible_collections.cisco.nac_dc_vxlan.plugins.action.helper_functions import has_keys


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = ['fabric', 'overlay_services', 'vrfs', 'vrf_attach_groups', 'networks', 'network_attach_groups']

    def prepare(self):
        model_data = self.kwargs['results']['model_extended']

        # Handle VRFs/Networks Under Overlay Services.  Need to create an empty list
        # if vrfs/networks or vrf/networks key is not present in the service model data
        if not has_keys(model_data, ['fabric', 'overlay_services']):
            model_data['fabric']['overlay_services'] = {'vrfs': []}
            model_data['fabric']['overlay_services'] = {'networks': []}
        if not has_keys(model_data, ['fabric', 'overlay_services', 'vrfs']):
            model_data['fabric']['overlay_services']['vrfs'] = []
        if not has_keys(model_data, ['fabric', 'overlay_services', 'networks']):
                model_data['fabric']['overlay_services']['networks'] = []

        # Rebuild sm_data['fabric']['overlay_services']['vrf_attach_groups'] into
        # a structure that is easier to use.
        if has_keys(model_data, ['fabric', 'overlay_services', 'vrf_attach_groups']):
            model_data['fabric']['overlay_services']['vrf_attach_groups_dict'] = {}
            for grp in model_data['fabric']['overlay_services']['vrf_attach_groups']:
                model_data['fabric']['overlay_services']['vrf_attach_groups_dict'][grp['name']] = []
                for switch in grp['switches']:
                    model_data['fabric']['overlay_services']['vrf_attach_groups_dict'][grp['name']].append(switch)

        # Rebuild sm_data['fabric']['overlay_services']['network_attach_groups'] into
        # a structure that is easier to use.
        if has_keys(model_data, ['fabric', 'overlay_services', 'network_attach_groups']):
            model_data['fabric']['overlay_services']['network_attach_groups_dict'] = {}
            for grp in model_data['fabric']['overlay_services']['network_attach_groups']:
                model_data['fabric']['overlay_services']['network_attach_groups_dict'][grp['name']] = []
                for switch in grp['switches']:
                    model_data['fabric']['overlay_services']['network_attach_groups_dict'][grp['name']].append(switch)

        self.kwargs['results']['model_extended'] = model_data
        return self.kwargs['results']

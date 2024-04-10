from ...helper_functions import data_model_key_check


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        model_data = self.kwargs['results']['model_extended']


        # Rebuild sm_data['fabric']['overlay_services']['vrf_attach_groups'] into
        # a structure that is easier to use.
        vrf_grp_name_list = []
        model_data['fabric']['overlay_services']['vrf_attach_groups_dict'] = {}
        for grp in model_data['fabric']['overlay_services']['vrf_attach_groups']:
            model_data['fabric']['overlay_services']['vrf_attach_groups_dict'][grp['name']] = []
            vrf_grp_name_list.append(grp['name'])
            for switch in grp['switches']:
                model_data['fabric']['overlay_services']['vrf_attach_groups_dict'][grp['name']].append(switch)


        # Remove attach_group from vrf if the group_name is not defined
        for vrf in model_data['fabric']['overlay_services']['vrfs']:
            if 'attach_group' in vrf:
                if vrf.get('attach_group') not in vrf_grp_name_list:
                    del vrf['attach_group']

        # Rebuild sm_data['fabric']['overlay_services']['network_attach_groups'] into
        # a structure that is easier to use.
        net_grp_name_list = []
        model_data['fabric']['overlay_services']['network_attach_groups_dict'] = {}
        for grp in model_data['fabric']['overlay_services']['network_attach_groups']:
            model_data['fabric']['overlay_services']['network_attach_groups_dict'][grp['name']] = []
            net_grp_name_list.append(grp['name'])
            for switch in grp['switches']:
                model_data['fabric']['overlay_services']['network_attach_groups_dict'][grp['name']].append(switch)

        # Remove attach_group from net if the group_name is not defined
        for net in model_data['fabric']['overlay_services']['networks']:
            if 'attach_group' in net:
                if net.get('attach_group') not in net_grp_name_list:
                    del net['attach_group']

        self.kwargs['results']['model_extended'] = model_data
        return self.kwargs['results']

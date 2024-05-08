
from ...helper_functions import data_model_key_check


def update_nested_dict(nested_dict, keys, new_value):
    if len(keys) == 1:
        nested_dict[keys[0]] = new_value
    else:
        key = keys[0]
        if key in nested_dict:
            update_nested_dict(nested_dict[key], keys[1:], new_value)


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def set_list_default(self, parent_keys, target_key):
        keys = parent_keys + [target_key]
        dm_check = data_model_key_check(self.model_data, keys)
        if target_key in dm_check['keys_not_found'] or \
           target_key in dm_check['keys_no_data']:
            update_nested_dict(self.model_data, keys, [])

    # The prepare method is used to default each list or nested list
    # in the model data to an empty list if the key for the list does
    # not exist or data under they key does not exist.
    #
    # This is to ensure that the model data is consistent and can be
    # used by other plugins without having to check if the key exists.
    def prepare(self):
        self.model_data = self.kwargs['results']['model_extended']

        # --------------------------------------------------------------------
        # Fabric Global List Defaults
        # --------------------------------------------------------------------

        # Check vxlan.global list elements
        parent_keys = ['vxlan', 'global']
        target_key = 'dns_servers'
        self.set_list_default(parent_keys, target_key)

        # keys = ['vxlan', 'global', 'ntp_servers']
        parent_keys = ['vxlan', 'global']
        target_key = 'ntp_servers'
        self.set_list_default(parent_keys, target_key)

        # --------------------------------------------------------------------
        # Fabric Topology List Defaults
        # --------------------------------------------------------------------

        # Check vxlan.topology list elements
        parent_keys = ['vxlan', 'topology']
        dm_check = data_model_key_check(self.model_data, parent_keys)
        if 'topology' in dm_check['keys_no_data']:
            self.model_data['vxlan']['topology'] = {'edge_connections': []}
            self.model_data['vxlan']['topology'] = {'fabric_links': []}
            self.model_data['vxlan']['topology'] = {'switches': []}
            self.model_data['vxlan']['topology'] = {'vpc_peers': []}

        # Check vxlan.topology.fabric_links list element
        target_key = 'fabric_links'
        self.set_list_default(parent_keys, target_key)

        # Check vxlan.topology.edge_connections list element
        target_key = 'edge_connections'
        self.set_list_default(parent_keys, target_key)

        # Check vxlan.topology.switches list element
        target_key = 'switches'
        self.set_list_default(parent_keys, target_key)

        # Check vxlan.topology.vpc_peers list element
        target_key = 'vpc_peers'
        self.set_list_default(parent_keys, target_key)

        # --------------------------------------------------------------------
        # Fabric Topology Switches Freeforms List Defaults
        # --------------------------------------------------------------------

        # Check vxlan.topology.switches[index].freeforms list elements
        list_index = 0
        for switch in self.model_data['vxlan']['topology']['switches']:
            dm_check = data_model_key_check(switch, ['freeforms'])
            if 'freeforms' in dm_check['keys_not_found'] or \
               'freeforms' in dm_check['keys_no_data']:
                self.model_data['vxlan']['topology']['switches'][list_index]['freeforms'] = []

            list_index += 1

        # --------------------------------------------------------------------
        # Fabric Topology Switches Interfaces List Defaults
        # --------------------------------------------------------------------

        # Check vxlan.topology.switches[index].interfaces list elements
        list_index = 0
        for switch in self.model_data['vxlan']['topology']['switches']:
            dm_check = data_model_key_check(switch, ['interfaces'])
            if 'interfaces' in dm_check['keys_not_found'] or 'interfaces' in dm_check['keys_no_data']:
                self.model_data['vxlan']['topology']['switches'][list_index]['interfaces'] = []

            list_index += 1

        # --------------------------------------------------------------------
        # Fabric Overlay List Defaults
        # --------------------------------------------------------------------

        # Check vxlan.overlay_services list elements
        parent_keys = ['vxlan', 'overlay_services']
        dm_check = data_model_key_check(self.model_data, parent_keys)
        if 'overlay_services' in dm_check['keys_no_data']:
            self.model_data['vxlan']['overlay_services'] = {'vrfs': []}
            self.model_data['vxlan']['overlay_services'] = {'vrf_attach_groups': []}
            self.model_data['vxlan']['overlay_services'] = {'networks': []}
            self.model_data['vxlan']['overlay_services'] = {'network_attach_groups': []}

        # Check vxlan.overlay_services.vrfs list element
        target_key = 'vrfs'
        self.set_list_default(parent_keys, target_key)

        # Check vxlan.overlay_services.vrf_attach_groups list element
        target_key = 'vrf_attach_groups'
        self.set_list_default(parent_keys, target_key)

        # Check vxlan.overlay_services.vrf_attach_groups[index].switches list elements
        list_index = 0
        for group in self.model_data['vxlan']['overlay_services']['vrf_attach_groups']:
            dm_check = data_model_key_check(group, ['switches'])
            if 'switches' in dm_check['keys_not_found'] or \
               'switches' in dm_check['keys_no_data']:
                self.model_data['vxlan']['overlay_services']['vrf_attach_groups'][list_index]['switches'] = []

            list_index += 1

        # Check vxlan.overlay_services.networks list element
        target_key = 'networks'
        self.set_list_default(parent_keys, target_key)

        # Check vxlan.overlay_services.network_attach_groups list element
        target_key = 'network_attach_groups'
        self.set_list_default(parent_keys, target_key)

        # Check vxlan.overlay_services.network_attach_groups[index].switches list elements
        list_index = 0
        for group in self.model_data['vxlan']['overlay_services']['network_attach_groups']:
            dm_check = data_model_key_check(group, ['switches'])
            if 'switches' in dm_check['keys_not_found'] or \
               'switches' in dm_check['keys_no_data']:
                self.model_data['vxlan']['overlay_services']['network_attach_groups'][list_index]['switches'] = []

            list_index += 1

        self.kwargs['results']['model_extended'] = self.model_data
        return self.kwargs['results']

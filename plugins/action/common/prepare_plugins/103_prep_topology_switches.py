from ...helper_functions import data_model_key_check


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        model_data = self.kwargs['results']['model_extended']

        model_data['fabric']['topology']['spine'] = {}
        model_data['fabric']['topology']['leaf'] = {}
        model_data['fabric']['topology']['border'] = {}
        sm_switches = model_data['fabric']['topology']['switches']
        for switch in sm_switches:
            # Build list of switch IP's based on role keyed by switch name
            name = switch.get('name')
            role = switch.get('role')
            model_data['fabric']['topology'][role][name] = {}
            v4_key = 'management_ipv4_address'
            v6_key = 'management_ipv6_address'
            v4ip = switch.get('management').get(v4_key)
            v6ip = switch.get('management').get(v6_key)
            model_data['fabric']['topology'][role][name][v4_key] = v4ip
            model_data['fabric']['topology'][role][name][v6_key] = v6ip

        self.kwargs['results']['model_extended'] = model_data
        return self.kwargs['results']

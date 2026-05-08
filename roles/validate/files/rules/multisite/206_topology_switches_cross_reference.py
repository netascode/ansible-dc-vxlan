from pathlib import Path
from json import load


class Rule:
    id = "206"
    description = "Cross check child fabric topology switches"
    severity = "HIGH"

    msg = "{0}"

    @classmethod
    def match(cls, data_model):
        results = []

        child_fabrics_switches = []
        vrf_attach_group_switches = []
        net_attach_group_switches = []

        validate_files_path = Path(__file__).parents[2]

        multisite_child_fabric_keys = ['vxlan', 'multisite', 'child_fabrics']
        check = cls.data_model_key_check(data_model, multisite_child_fabric_keys)
        if 'child_fabrics' in check['keys_found'] and 'child_fabrics' in check['keys_data']:
            dm_child_fabrics = cls.safeget(data_model, multisite_child_fabric_keys)
            for child_fabric in dm_child_fabrics:
                service_model_filename = f"{child_fabric['name']}_service_model_golden.json"
                service_model_path = validate_files_path / service_model_filename
                try:
                    with open(service_model_path, "r") as service_model_file:
                        service_model = load(service_model_file)
                except FileNotFoundError:
                    results.append(cls.msg.format(f"{service_model_filename} file not found. Run role_validate against the child fabrics."))
                else:
                    child_fabrics_switches.extend(switch['name'] for switch in service_model.get('vxlan', {}).get('topology', {}).get('switches', []))

        multisite_vrf_attach_group_keys = ['vxlan', 'multisite', 'overlay', 'vrf_attach_groups']
        check = cls.data_model_key_check(data_model, multisite_vrf_attach_group_keys)
        if 'vrf_attach_groups' in check['keys_found'] and 'vrf_attach_groups' in check['keys_data']:
            dm_msite_vrf_attach_groups = cls.safeget(data_model, multisite_vrf_attach_group_keys)
            for attach_group in dm_msite_vrf_attach_groups:
                vrf_attach_group_switches.extend(switch['hostname'] for switch in attach_group['switches'])
            for vag_switch in vrf_attach_group_switches:
                if vag_switch not in child_fabrics_switches:
                    results.append(cls.msg.format(f"{vag_switch} not pressent in child fabrics topology switches."))

        multisite_net_attach_group_keys = ['vxlan', 'multisite', 'overlay', 'network_attach_groups']
        check = cls.data_model_key_check(data_model, multisite_net_attach_group_keys)
        if 'network_attach_groups' in check['keys_found'] and 'network_attach_groups' in check['keys_data']:
            dm_msite_net_attach_groups = cls.safeget(data_model, multisite_net_attach_group_keys)
            for attach_group in dm_msite_net_attach_groups:
                net_attach_group_switches.extend(switch['hostname'] for switch in attach_group['switches'])
            for nag_switch in net_attach_group_switches:
                if nag_switch not in child_fabrics_switches:
                    results.append(cls.msg.format(f"{nag_switch} not pressent in child fabrics topology switches."))

        return results

    @classmethod
    def data_model_key_check(cls, tested_object, keys):
        dm_key_dict = {'keys_found': [], 'keys_not_found': [], 'keys_data': [], 'keys_no_data': []}
        for key in keys:
            if tested_object and key in tested_object:
                dm_key_dict['keys_found'].append(key)
                tested_object = tested_object[key]
                if tested_object:
                    dm_key_dict['keys_data'].append(key)
                else:
                    dm_key_dict['keys_no_data'].append(key)
            else:
                dm_key_dict['keys_not_found'].append(key)
        return dm_key_dict

    @classmethod
    def safeget(cls, dict, keys):
        # Utility function to safely get nested dictionary values
        for key in keys:
            if dict is None:
                return None
            if key in dict:
                dict = dict[key]
            else:
                return None

        return dict

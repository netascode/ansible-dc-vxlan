import re


class Rule:
    id = "322"
    description = "Verify fabric links are not defined more than once"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        fabric_links = []

        check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'fabric_links'])
        if 'fabric_links' in check['keys_data']:
            fabric_links = data_model.get("vxlan").get("topology").get("fabric_links")
        else:
            return results

        # A link and its reverse (source/dest swapped) are the same link, matching how
        # existing_links_check and links_filter_and_remove compare links.
        seen_links = {}
        for fabric_link in fabric_links:
            source = (str(fabric_link.get("source_device", "")).lower(), cls.normalize_interface_name(fabric_link.get("source_interface", "")))
            dest = (str(fabric_link.get("dest_device", "")).lower(), cls.normalize_interface_name(fabric_link.get("dest_interface", "")))
            link_name = (
                f"{fabric_link.get('source_device')}:{fabric_link.get('source_interface')} -> "
                f"{fabric_link.get('dest_device')}:{fabric_link.get('dest_interface')}"
            )
            link_key = frozenset((source, dest))
            if link_key in seen_links:
                results.append(
                    f"vxlan.topology.fabric_links.{link_name} is defined more than once "
                    f"(first defined as {seen_links[link_key]}). Duplicate encountered."
                )
            else:
                seen_links[link_key] = link_name

        return results

    # Normalize interface name the same way as the ndfc_fabric_links.j2 template (e1/1, eth1/1 -> ethernet1/1)
    @classmethod
    def normalize_interface_name(cls, interface_name):
        return re.sub(r'^(?:e|eth|ethernet)(?=\d)', 'ethernet', str(interface_name).strip().lower())

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

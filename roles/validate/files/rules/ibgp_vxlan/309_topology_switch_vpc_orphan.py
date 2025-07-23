class Rule:
    id = "309"
    description = "Verify orphan ports for non-VPC switches"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        switches = []

        # Check for the 'switches' key in the data model
        dm_check = cls.data_model_key_check(inventory, ['vxlan', 'topology', 'switches'])
        if 'switches' in dm_check['keys_data']:
            switches = inventory['vxlan']['topology']['switches']

        # Extract all VPC peer switch names from vxlan.topology.vpc_peers
        vpc_peers = set()
        vpc_peers_check = cls.data_model_key_check(inventory, ['vxlan', 'topology', 'vpc_peers'])
        if 'vpc_peers' in vpc_peers_check['keys_data']:
            for peer in inventory['vxlan']['topology']['vpc_peers']:
                vpc_peers.add(peer['peer1'])
                vpc_peers.add(peer['peer2'])

        # Iterate through switches and their interfaces
        for switch in switches:
            switch_name = switch.get('name')
            if switch.get("interfaces"):
                for interface in switch["interfaces"]:
                    interface_name = interface.get('name')

                    # Check if orphan_port is true
                    if interface.get('orphan_port', False):
                        # Fail if switch.name is not in vpc_peers
                        if switch_name not in vpc_peers:
                            results.append(
                                f"Switch '{switch_name}' with interface '{interface_name}' "
                                "has orphan_port: true, but the switch is not part of any VPC peer."
                            )

        return results

    @classmethod
    def data_model_key_check(cls, tested_object, keys):
        """
        Helper method to check the presence of keys in a nested dictionary structure.
        """
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

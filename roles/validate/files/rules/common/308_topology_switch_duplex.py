class Rule:
    id = "308"
    description = "Verify interface duplex mode"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        switches = []

        # Check for the 'switches' key in the data model
        dm_check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' in dm_check['keys_data']:
            switches = data_model['vxlan']['topology']['switches']

        # Iterate through switches and their interfaces
        for switch in switches:
            if switch.get("interfaces"):
                for interface in switch["interfaces"]:
                    interface_name = interface.get('name')

                    # Extract duplex and speed values
                    duplex = interface.get('duplex')
                    speed = interface.get('speed')

                    # Condition 1: duplex is not supported without speed
                    # (EXCEPT when duplex is 'auto')
                    if duplex and duplex != 'auto' and not speed:
                        results.append(
                            f"vxlan.topology.switches.interfaces.{interface_name}.duplex "
                            f"is not supported without speed on switch {switch.get('name')}"
                        )

                    # Condition 2: duplex: 'half' or 'full' is not supported if speed == 'auto'
                    if duplex in ['half', 'full'] and speed == 'auto':
                        results.append(
                            f"vxlan.topology.switches.interfaces.{interface_name}.duplex "
                            f"'{duplex}' is not supported with speed 'auto' on switch {switch.get('name')}"
                        )

                    # Condition 3: duplex: 'half' is only supported with speed: '100mb'
                    if duplex == 'half' and speed != '100mb':
                        results.append(
                            f"vxlan.topology.switches.interfaces.{interface_name}.duplex 'half' "
                            f"is only supported with speed '100mb' on switch {switch.get('name')}"
                        )

                    # Condition 4: duplex: 'auto' supports all speed values (or no speed at all)
                    if duplex == 'auto':
                        # No validation needed as all speed values (or absence of speed)
                        # are supported
                        continue

                    # Condition 5: speed: 'auto' supports all duplex values (or no duplex at all)
                    if speed == 'auto':
                        # No validation needed as all speed values (or absence of speed)
                        # are supported
                        continue

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

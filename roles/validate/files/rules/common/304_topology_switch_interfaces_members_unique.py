import re


class Rule:
    id = "304"
    description = "\n1)Verify Interface names are Unique per switch\n2)Verify member interfaces are not repeated within a switch\n"
    severity = "HIGH"

    # Check if interface names are unique per switch and member interfaces are not repeated within a switch
    @classmethod
    def match(cls, data_model):
        results = []
        # Check if fabric topology switches are defined
        switches = []
        if data_model.get("vxlan", None):
            if data_model["vxlan"].get("topology", None):
                if data_model.get("vxlan").get("topology").get("switches", None):
                    switches = data_model.get("vxlan").get("topology").get("switches")
        for switch in switches:
            # Check if interfaces are defined
            if switch.get("interfaces"):
                # Initialize lists to store interface names and member interface names
                interface_names = []
                member_interface_names = []
                # Iterate through interfaces
                for interface in switch.get("interfaces"):
                    # Normalize interface name
                    interface_name = cls.normalize_interface_name(interface.get("name"))
                    # Check if interface name is unique, by checking the list of interface names already parsed
                    if interface_name in interface_names:
                        # Append error message to results
                        results.append(
                            f"vxlan.topology.switches.{switch['name']}.interfaces.{interface_name}. "
                            "This interface is defined more than once within this switch. Duplicate encountered"
                        )
                    # Append interface name to list of interface names if unique
                    else:
                        interface_names.append(interface_name)
                    # Check if member interfaces are defined
                    if interface.get("members"):
                        # Iterate through member interfaces
                        for member_interface in interface.get("members"):
                            # Normalize member interface name
                            member_interface_name = cls.normalize_interface_name(
                                member_interface
                            )
                            # Check if member interface name is repeated within the switch, by checking the list of member interface names already parsed
                            if member_interface_name in member_interface_names:
                                # Append error message to results
                                results.append(
                                    f"vxlan.topology.switches.{switch['name']}.interfaces.{interface_name}.members.{member_interface_name}. "
                                    "This interface is defined as a member of more than one Port-channel interfaces"
                                )
                            # Append member interface name to list of member interface names if unique
                            else:
                                member_interface_names.append(member_interface_name)
        return results

    # Normalize interface name
    @classmethod
    def normalize_interface_name(cls, interface_name):
        # Replace 'eth' or 'e' followed by digits with 'Ethernet' followed by the same digits
        interface_name = re.sub(
            r"(?i)^(?:e|eth(?:ernet)?)(\d(?:\/\d+){1,2})$",
            r"Ethernet\1",
            interface_name,
            flags=re.IGNORECASE,
        )

        # Replace 'Po' followed by digits with 'Port-channel' followed by the same digits
        interface_name = re.sub(
            r"(?i)^(po|port-channel)([1-9]|[1-9][0-9]{1,3}|[1-3][0-9]{3}|40([0-8][0-9]|9[0-6]))$",
            r"Port-channel\2",
            interface_name,
            flags=re.IGNORECASE,
        )

        # Replace 'eth' or 'e' followed by digits with 'Ethernet' followed by the same digits (for sub interface)
        interface_name = re.sub(
            r"(?i)^(?:e|eth(?:ernet)?)(\d(?:\/\d+){1,2}\.\d{1,4})$",
            r"Ethernet\1",
            interface_name,
            flags=re.IGNORECASE,
        )

        # Replace 'Lo' or 'Loopback' followed by digits with 'Loopback' followed by the same digits
        interface_name = re.sub(
            r"(?i)^(lo|loopback)([0-9]|[1-9][0-9]{1,2}|10[0-1][0-9]|102[0-3])$",
            r"Loopback\2",
            interface_name,
            flags=re.IGNORECASE,
        )

        return interface_name

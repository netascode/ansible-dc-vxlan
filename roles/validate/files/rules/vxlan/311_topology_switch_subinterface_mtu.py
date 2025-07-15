import re

class Rule:
    id = "311"
    description  = "Verify that the physical interface MTU is greater equal than all the sub-interfaces"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []
        switches = []
        default_routed_int_mtu = 9216 # from topology_switch_routed_interface
        default_port_channel_mtu = 9216 # from topology_switch_routed_po_interface
        default_sub_int_mtu = 9216 #  from topology_switch_routed_sub_interface

        switches = cls.safeget(inventory, ['vxlan', 'topology', 'switches'])

        for switch in switches:            
            if switch.get('interfaces'):
                interfaces_mtu = {}
                sub_interfaces_mtu = {}

                for interface in switch.get('interfaces'):
                    interface_mode = interface.get('mode')
                    inventory_interface_name = interface.get('name')
                    if 'routed' == interface_mode:
                        interface_name = cls.normalize_interface_name(inventory_interface_name)
                        if interface.get('mtu'):
                            mtu = interface.get('mtu')
                        else:
                            mtu = default_routed_int_mtu
                        interfaces_mtu[interface_name] = mtu
                    elif 'routed_po' == interface_mode:
                        interface_name = cls.normalize_interface_name(inventory_interface_name)
                        if interface.get('mtu'):
                            mtu = interface.get('mtu')
                        else:
                            mtu = default_port_channel_mtu
                        interfaces_mtu[interface_name] = mtu
                    elif 'routed_sub' == interface_mode:
                        sub_interface_name = cls.normalize_interface_name(inventory_interface_name)
                        if interface.get('mtu'):
                            mtu = interface.get('mtu')
                        else:
                            mtu = default_sub_int_mtu
                        sub_interfaces_mtu[sub_interface_name] = mtu

                for sub_interface_name in sub_interfaces_mtu:
                    interface_name = sub_interface_name.split('.')[0]
                    sub_interface_mtu = sub_interfaces_mtu[sub_interface_name]
                    if  interface_name in interfaces_mtu:
                        interface_mtu = interfaces_mtu[interface_name]
                    elif 'ether' in interface_name:
                        interface_mtu = default_routed_int_mtu
                    else:
                        interface_mtu = default_port_channel_mtu

                    if  sub_interface_mtu > interface_mtu:
                        results.append(
                            f"vxlan.topology.switches.{switch['name']}.interfaces.{sub_interface_name} ({sub_interface_mtu}). "
                            f"This interface MTU value is greater than the defined value of {interface_name} ({interface_mtu})."
                        )

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
    
    @classmethod
    def safeget(cls, dict, keys):
        """
        Utility function to safely get nested dictionary values
        """
        for key in keys:
            if dict is None:
                return None
            if key in dict:
                dict = dict[key]
            else:
                return None

        return dict
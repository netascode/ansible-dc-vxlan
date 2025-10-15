import re


class Rule:
    id = "310"
    description = "Verify if interfaces with sub-levels are part of the defined interface breakouts"
    severity = "HIGH"
    
    # Compiled regex patterns for better performance
    # FEX pattern: Ethernet[101-199]/1/[1-99]
    FEX_PATTERN = re.compile(r'^e(?:th(?:ernet)?)?1(0[1-9]|[1-9][0-9])/1/([1-9]|[1-9][0-9])$', re.IGNORECASE)
    
    # Breakout pattern: Ethernet[1-99]/[1-99]/[1-4]
    BREAKOUT_PATTERN = re.compile(r'^e(?:th(?:ernet)?)?([1-9]|[1-9][0-9])/([1-9]|[1-9][0-9])/([1-4])$', re.IGNORECASE)

    @classmethod
    def match(cls, data_model):
        # Reset results at the start of each call to avoid retaining previous results
        results = []

        # Extract switches from the data_model
        switches = data_model.get("vxlan", {}).get("topology", {}).get("switches", [])
        if switches is None:
            return results

        # Process each switch
        for switch in switches:
            # Extract interface breakouts and interfaces
            interface_breakouts = switch.get("interface_breakouts", [])
            interfaces = switch.get("interfaces", [])

            # Check for invalid breakout configurations
            for breakout in interface_breakouts:
                if "to" in breakout and breakout["from"] > breakout["to"]:
                    results.append(
                        f"Invalid breakout configuration on vxlan.topology.switches."
                        f"{switch['name']}.interface_breakouts: "
                        f"'from' ({breakout['from']}) is greater than 'to' ({breakout['to']})"
                    )

            # Check each interface
            for interface in interfaces:
                interface_name = interface.get("name", "")
                
                # Check if it's a FEX interface - skip validation
                if cls.FEX_PATTERN.match(interface_name):
                    continue
                
                # Check if it's a breakout interface pattern
                match = cls.BREAKOUT_PATTERN.match(interface_name)
                if match:
                    # Extract module, port, sub_level from regex groups
                    module_num = int(match.group(1))
                    port_num = int(match.group(2))
                    
                    # Verify if this breakout interface is defined in interface_breakouts
                    if not cls.is_interface_in_breakouts(module_num, port_num, interface_breakouts):
                        results.append(
                            f"Interface {interface_name} on vxlan.topology.switches."
                            f"{switch['name']} is not part of the interface breakouts"
                        )

        return results

    @staticmethod
    def is_interface_in_breakouts(module_num, port_num, breakouts):
        """
        Check if the given interface is part of the interface_breakouts.

        Parameters:
        - module_num (int): The module number (e.g., 1 from Ethernet1/x/y).
        - port_num (int): The port number (e.g., 5 from Ethernet1/5/y).
        - breakouts (list): List of interface breakout definitions.

        Returns:
        - bool: True if the interface is part of the breakouts, False otherwise.
        """
        # If no breakouts defined, interface cannot be valid
        if not breakouts:
            return False
        
        # Check each breakout definition
        for breakout in breakouts:
            if breakout.get("module") == module_num:
                # Check if port is in range (for range breakouts) or matches (for single-port)
                if "to" in breakout:
                    if breakout["from"] <= port_num <= breakout["to"]:
                        return True
                elif breakout.get("from") == port_num:
                    return True
        
        return False

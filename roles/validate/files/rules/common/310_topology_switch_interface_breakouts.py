import re

class Rule:
    id = "310"
    description = "Verify if interfaces with sub-levels are part of the defined interface breakouts"
    severity = "HIGH"
    
    # FEX regex pattern: Ethernet[101-199]/1/[1-99]
    FEX_PATTERN = re.compile(r'^e(?:th(?:ernet)?)?1(0[1-9]|[1-9][0-9])/1/([1-9]|[1-9][0-9])$', re.IGNORECASE)

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
                normalized_interface = interface_name.lower().replace("ethernet", "e").replace("eth", "e")
                
                # Check if it's a FEX interface - skip validation
                if cls.FEX_PATTERN.match(interface_name):
                    continue
                
                # Skip interfaces without sub-levels (e.g., E1/x)
                if cls.has_sub_level(normalized_interface):
                    if not cls.is_interface_in_breakouts(normalized_interface, interface_breakouts):
                        results.append(
                            f"Interface {interface_name} on vxlan.topology.switches."
                            f"{switch['name']} is not part of the interface breakouts"
                        )

        return results

    @staticmethod
    def has_sub_level(interface_name):
        """
        Check if an interface has a sub-level (e.g., E1/x/y).

        Parameters:
        - interface_name (str): The interface name to check.

        Returns:
        - bool: True if the interface has a sub-level, False otherwise.
        """
        parts = interface_name.split("/")
        return len(parts) == 3  # Check if the interface has exactly 3 parts (e.g., E1/x/y)

    @staticmethod
    def is_interface_in_breakouts(interface_name, breakouts):
        """
        Check if the given interface is part of the interface_breakouts.

        Parameters:
        - interface_name (str): The interface name to check (e.g., e1/100/3, Eth1/99/3).
        - breakouts (list): List of interface breakout definitions.

        Returns:
        - bool: True if the interface is part of the breakouts, False otherwise.
        """
        # Extract module and port details from the normalized interface name
        try:
            module, port, sub_level = interface_name.split("/")
            port = int(port)  # Convert port to an integer
        except ValueError:
            return False  # If the interface name is invalid or port conversion fails, return False

        # Check each breakout definition
        for breakout in breakouts:
            # Ensure the 'from' value is less than or equal to the 'to' value
            if breakout["module"] == int(module[1:]):  # Compare module numbers
                if "to" in breakout:  # Range breakout
                    if breakout["from"] <= port <= breakout["to"]:
                        return True
                elif breakout["from"] == port:  # Single-port breakout
                    return True

        return False
class Rule:
    id = "207"
    description = "Verify fabric replication and spine roles."
    severity = "HIGH"

    @classmethod
    def check_role(cls, data_model):
        """
        Check if any switch in the topology has the role
        'border_gateway_spine' or 'border_gateway'.
        Returns True if at least one such switch exists,
        otherwise False.
        Also sets a class-level variable with the
        serial_number of the first matching switch.
        """
        topology = data_model.get("vxlan", {}).get("topology", {})
        switches = topology.get("switches")
        if not switches:
            return False
        for switch in switches:
            if switch.get("role") in (
                "border_gateway_spine", "border_gateway"
            ):
                cls.matching_serial_number = switch.get("serial_number")
                cls.matching_role = switch.get("role")
                return True
        return False

    @classmethod
    def check_ipv6_underlay(cls, data_model):
        """
        Check if IPv6 underlay is enabled in the VXLAN configuration.
        Returns True if enabled, otherwise False.
        """
        return (
            data_model.get("vxlan", {})
            .get("underlay", {})
            .get("general", {})
            .get("enable_ipv6_underlay") is True
        )

    @classmethod
    def match(cls, data_model):
        """
        Main validation method.
        Checks if the combination of:
          - border_gateway_spine or border_gateway role present,
          - IPv6 underlay enabled,
          - replication_mode set to 'ingress'
        is present in the data_model.
        If so, appends a descriptive error message to the results list.
        Returns the list of validation errors (empty if none).
        """
        results = []
        fabric_replication = False
        border_gateway_role = cls.check_role(data_model)
        ipv6_underlay = cls.check_ipv6_underlay(data_model)

        # Retrieve the replication_mode value if present
        if data_model.get("vxlan", None):
            if data_model["vxlan"].get("underlay", None):
                if data_model["vxlan"].get("underlay").get("general", None):
                    fabric_replication = (
                        data_model["vxlan"]["underlay"]["general"].get(
                            "replication_mode", False
                        )
                    )

        # Validate the combination and add an error if the rule is violated
        if border_gateway_role and ipv6_underlay and (
            fabric_replication == "ingress"
        ):
            results.append(
                f"The switch {cls.matching_serial_number} is set to "
                f"{cls.matching_role} role."
            )
            results.append(
                "For replication_mode to be set to "
                "ingress and ipv6 underlay enabled, "
                "switches.role must NOT be set to "
                "border_gateway_spine or border_gateway."
            )

        return results

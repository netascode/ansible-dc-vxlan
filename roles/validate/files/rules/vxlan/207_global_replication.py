class Rule:
    id = "207"
    description = "Verify fabric replication and spine roles."
    severity = "HIGH"

    @classmethod
    def check_role(cls, inventory):
        """
        Check if any switch in the topology has the role 'border_gateway_spine' or 'border_gateway'.
        Returns True if at least one such switch exists, otherwise False.
        """
        topology = inventory.get("vxlan", {}).get("topology", {})
        switches = topology.get("switches")
        if not switches:
            return False
        return any(switch.get("role") in ("border_gateway_spine", "border_gateway") for switch in switches)

    @classmethod
    def check_ipv6_underlay(cls, inventory):
        """
        Check if IPv6 underlay is enabled in the VXLAN configuration.
        Returns True if enabled, otherwise False.
        """
        return inventory.get("vxlan", {}) \
                   .get("underlay", {}) \
                   .get("general", {}) \
                   .get("enable_ipv6_underlay") is True

    @classmethod
    def match(cls, inventory):
        """
        Main validation method.
        Checks if the combination of:
          - border_gateway_spine or border_gateway role present,
          - IPv6 underlay enabled,
          - replication_mode set to 'ingress'
        is present in the inventory.
        If so, appends a descriptive error message to the results list.
        Returns the list of validation errors (empty if none).
        """
        results = []
        fabric_replication = False
        border_gateway_role = cls.check_role(inventory)
        ipv6_underlay = cls.check_ipv6_underlay(inventory)

        # Retrieve the replication_mode value if present
        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("underlay", None):
                if inventory["vxlan"].get("underlay").get("general", None):
                    fabric_replication = inventory["vxlan"]["underlay"]["general"].get("replication_mode", False)

        # Validate the combination and add an error if the rule is violated
        if border_gateway_role and ipv6_underlay and (fabric_replication == "ingress"):
            results.append(
                "For vxlan.underlay.general.replication_mode to be set to ingress, "
                "vxlan.topology.switches.role must not be set to border_gateway_spine or border_gateway and "
                "vxlan.underlay.general.enable_ipv6_underlay must not be set to true."
            )

        return results

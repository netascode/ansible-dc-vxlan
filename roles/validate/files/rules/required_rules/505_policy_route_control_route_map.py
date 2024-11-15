"""
Validation Rules scenarios:
1.  Switches in the vxlan.overlay_extensions.route_control.switches should be defined in the vxlan.topology.switches
2.  Groups in the vxlan.overlay_extensions.route_control.switches.group should be defined in the vxlan.overlay_extensions.route_control.groups
3.  Route maps in the vxlan.overlay_extensions.route_control.groups.route_maps should be defined in the vxlan.overlay_extensions.route_control.route_maps
4.  MAC list in vxlan.overlay_extensions.route_control.groups.mac_lists ishould be defined in vxlan.overlay_extensions.route_control.mac_lists
5.  Standard community lists in the vxlan.overlay_extensions.route_control.groups.standard_community_lists should be defined in the vxlan.overlay_extensions.route_control.standard_community_lists
6.  Extended community lists in the vxlan.overlay_extensions.route_control.groups.extended_community_lists should be defined in the vxlan.overlay_extensions.route_control.extended_community_lists
7.  IPv4 prefix lists in the vxlan.overlay_extensions.route_control.groups.ipv4_prefix_lists should be defined in the vxlan.overlay_extensions.route_control.ipv4_prefix_lists
8.  IPv6 prefix lists in the vxlan.overlay_extensions.route_control.groups.ipv6_prefix_lists should be defined in the vxlan.overlay_extensions.route_control.ipv6_prefix_lists
9.  IPv4 access lists in the vxlan.overlay_extensions.route_control.groups.ipv4_access_lists should be defined in the vxlan.overlay_extensions.route_control.ipv4_access_lists
10. Time ranges in the vxlan.overlay_extensions.route_control.groups.time_ranges should be defined in the vxlan.overlay_extensions.route_control.time_ranges
11. IPv4 object groups in the vxlan.overlay_extensions.route_control.groups.ipv4_object_groups should be defined in the vxlan.overlay_extensions.route_control.ipv4_object_groups
12. IPv6 object groups in the vxlan.overlay_extensions.route_control.groups.ipv6_object_groups should be defined in the vxlan.overlay_extensions.route_control.ipv6_object_groups.
13. Name for each of these policies should be unique when they are created and when they are consumed
14. Check if in the set_metric route map if we use metric bandwith or all the five metrics: bandwidth, delay, reliability, load, mtu
"""


class Rule:
    """
    Class 505 - Verify Route-Control Cross Reference Between Policies, Groups, and Switches
    """

    id = "505"
    description = (
        "Verify Route-Control Cross Reference Between Policies, Groups, and Switches"
    )
    severity = "HIGH"
    results = []

    @classmethod
    def match(cls, data):
        """
        function used by iac-validate
        """
        route_control = []
        topology_switches = []
        switch_policy = []
        group_policy = []

        # Get fabric switches
        if data.get("vxlan"):
            if data["vxlan"].get("topology"):
                if data.get("vxlan").get("topology").get("switches"):
                    topology_switches = (
                        data.get("vxlan").get("topology").get("switches")
                    )

        # Get route_control policies
        if data.get("vxlan", None):
            if data["vxlan"].get("overlay_extensions", None):
                if data["vxlan"].get("overlay_extensions").get("route_control", None):
                    route_control = data["vxlan"]["overlay_extensions"]["route_control"]
                    # Get groups policies
                    if data["vxlan"].get("overlay_extensions").get("route_control").get("groups", None):
                        group_policy = data["vxlan"]["overlay_extensions"]["route_control"]["groups"]
                else:
                    # route control is empty
                    return cls.results

        # Check switch Level
        if route_control.get("switches"):
            for switch_policy in route_control["switches"]:
                cls.check_switch_level(
                    switch_policy,
                    topology_switches,
                    group_policy
                )

        # Check route maps
        if route_control.get("route_maps"):
            for route_map in route_control["route_maps"]:
                if route_map.get("entries", None):
                    for seq_numer in route_map["entries"]:
                        if seq_numer.get("set", None):
                            # Check set metric integrity
                            cls.check_set_metric_integrity(
                                seq_numer["set"]
                            )

        return cls.results

    @classmethod
    def check_switch_level(
        cls,
        switch_policy,
        topology_switches,
        group_policy
    ):
        """
        Check switch level
        """

        # Check if switch exists in topology
        cls.check_switch_in_topology(
            switch_policy["name"], topology_switches
        )

        if switch_policy.get("groups"):
            for switch_group in switch_policy["groups"]:
                cls.check_group_in_switch(
                    switch_group,
                    group_policy
                )

    @classmethod
    def check_switch_in_topology(cls, switch, topology_switches):
        """
        Check if switch is in the topology
        """
        if list(filter(lambda topo: topo["name"] == switch, topology_switches)):
            pass
        else:
            cls.results.append(
                f"vxlan.overlay_extensions.route_control.switches.{switch} "
                "is not defined in vxlan.topology.switches"
            )

    @classmethod
    def check_group_in_switch(cls, switch_group, group_policy):
        """
        Check if group in switch is defined in route_control
        """
        if list(filter(lambda group: group["name"] == switch_group, group_policy)):
            pass
        else:
            cls.results.append(
                f"vxlan.overlay_extensions.route_control.switches.groups.{switch_group} "
                "is not defined in vxlan.overlay_extensions.route_control.groups"
            )

    @classmethod
    def check_set_metric_integrity(cls, set_policy):
        """
        Check if in the set_metric route map if we use metric bandwith or all the five metrics: bandwidth, delay, reliability, load, mtu
        """
        if set_policy.get("metric", None):
            metrics = ['bandwidth', 'delay', 'reliability', 'load', 'mtu']
            if 'bandwidth' in set_policy["metric"][0].keys() and len(set_policy["metric"][0].keys()) == 1:
                pass
            else:
                for metric in metrics:
                    if metric not in list(set_policy["metric"][0].keys()):
                        cls.results.append(
                            "For vxlan.overlay_extensions.route_control.route_maps.entries.set.metric to be enabled, " +
                            metric + " must be set in the metric.")

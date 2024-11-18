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
        route_maps = []
        group_policies = []

        # Get route_control policies
        if data.get("vxlan", None):
            if data["vxlan"].get("overlay_extensions", None):
                if data["vxlan"].get("overlay_extensions").get("route_control", None):
                    route_control = data["vxlan"]["overlay_extensions"]["route_control"]
                    # Get groups policies
                    if data["vxlan"].get("overlay_extensions").get("route_control").get("groups", None):
                        group_policies = data["vxlan"]["overlay_extensions"]["route_control"]["groups"]
                    else:
                        # group is empty
                        return cls.results
                    if data["vxlan"].get("overlay_extensions").get("route_control").get("route_maps", None):
                        route_maps = data["vxlan"]["overlay_extensions"]["route_control"]["route_maps"]
                else:
                    # route control is empty
                    return cls.results

        # Get fabric switches
        if data.get("vxlan"):
            if data["vxlan"].get("topology"):
                if data.get("vxlan").get("topology").get("switches"):
                    topology_switches = (
                        data.get("vxlan").get("topology").get("switches")
                    )

        # Check switch Level
        if route_control.get("switches"):
            for switch_policy in route_control["switches"]:
                cls.check_switch_level(
                    switch_policy,
                    topology_switches,
                    group_policies
                )

        cls.check_route_maps(
            route_maps
        )

        return cls.results

    @classmethod
    def check_switch_level(
        cls,
        switch_policy,
        topology_switches,
        group_policies
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
                    group_policies
                )

    @classmethod
    def check_switch_in_topology(
        cls,
        switch,
        topology_switches
    ):
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
    def check_group_in_switch(
        cls,
        switch_group,
        group_policies
    ):
        """
        Check if group in switch is defined in route_control
        """
        if list(filter(lambda group: group["name"] == switch_group, group_policies)):
            pass
        else:
            cls.results.append(
                f"vxlan.overlay_extensions.route_control.switches.groups.{switch_group} "
                "is not defined in vxlan.overlay_extensions.route_control.groups"
            )

    @classmethod
    def check_route_maps(
        cls,
        route_maps
    ):
        """
        Check if route_maps integrity
        """

        # Check route maps
        for route_map in route_maps:
            if route_map.get("entries", None):
                # Check set metric integrity
                cls.check_route_maps_entries(
                    route_map["entries"]
                )

    @classmethod
    def check_route_maps_entries(
        cls,
        entries
    ):
        """
        Check if route_maps entries integrity
        """

        # Check route maps entries
        for seq_numer in entries:
            if seq_numer.get("set", None):
                for sets in seq_numer["set"]:
                    if sets.get("metric", None):
                        # Check set metric integrity
                        cls.check_set_metric_integrity(
                            sets["metric"]
                        )

    @classmethod
    def check_set_metric_integrity(
        cls,
        set_metric
    ):
        """
        Check if in the set_metric route map if we use metric bandwith or all the five metrics: bandwidth, delay, reliability, load, mtu
        """

        metrics = ['bandwidth', 'delay', 'reliability', 'load', 'mtu']
        if 'bandwidth' in set_metric and len(set_metric) == 1:
            pass
        else:
            for metric in metrics:
                if metric not in set_metric:
                    cls.results.append(
                        "For vxlan.overlay_extensions.route_control.route_maps.entries.set.metric to be enabled, " +
                        metric + " must be set in the metric.")

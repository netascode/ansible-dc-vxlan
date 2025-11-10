"""
Validation Rules scenarios:
1.  Switches in the vxlan.overlay_extensions.route_control.switches should be defined in the vxlan.topology.switches
2.  Groups in the vxlan.overlay_extensions.route_control.switches.group should be defined in the vxlan.overlay_extensions.route_control.groups
3.  Route maps in the vxlan.overlay_extensions.route_control.groups.route_maps should be defined in the vxlan.overlay_extensions.route_control.route_maps
4.  MAC list in vxlan.overlay_extensions.route_control.groups.mac_lists should be defined in vxlan.overlay_extensions.route_control.mac_lists
5.  Standard community lists in the vxlan.overlay_extensions.route_control.groups.standard_community_lists should be defined in the
    vxlan.overlay_extensions.route_control.standard_community_lists
6.  Extended community lists in the vxlan.overlay_extensions.route_control.groups.extended_community_lists should be defined in the
    vxlan.overlay_extensions.route_control.extended_community_lists
7.  IPv4 prefix lists in the vxlan.overlay_extensions.route_control.groups.ipv4_prefix_lists should be defined in the
    vxlan.overlay_extensions.route_control.ipv4_prefix_lists
8.  IPv6 prefix lists in the vxlan.overlay_extensions.route_control.groups.ipv6_prefix_lists should be defined in the
    vxlan.overlay_extensions.route_control.ipv6_prefix_lists
9.  IPv4 access lists in the vxlan.overlay_extensions.route_control.groups.ipv4_access_lists should be defined in the
    vxlan.overlay_extensions.route_control.ipv4_access_lists
10. Time ranges in the vxlan.overlay_extensions.route_control.groups.time_ranges should be defined in the vxlan.overlay_extensions.route_control.time_ranges
11. IPv4 object groups in the vxlan.overlay_extensions.route_control.groups.ipv4_object_groups should be defined in the
    vxlan.overlay_extensions.route_control.ipv4_object_groups
12. IPv6 object groups in the vxlan.overlay_extensions.route_control.groups.ipv6_object_groups should be defined in the
    vxlan.overlay_extensions.route_control.ipv6_object_groups.
13. Name for each of these policies should be unique when they are consumed in a group
14. Check if in the set_metric route map only metric bandwith is used or alternatively all the five metrics are used: bandwidth, delay, reliability, load, mtu
15. Check if in set ip/ipv6 next-hop verify-availability route map next-hops is configured
"""


class Rule:
    """
    Class 505 - Verify route control cross reference between policies, groups, and switches
    """

    id = "505"
    description = "Verify route control cross reference between policies, groups, and switches"
    severity = "HIGH"
    results = []

    route_control_objects_names = ["ip_as_path_access_lists", "route_maps",
                                   "mac_list", "standard_community_lists", "extended_community_lists",
                                   "ipv4_access_lists", "ipv6_access_lists",
                                   "ipv4_prefix_lists", "ipv6_prefix_lists",
                                   "time_range", "ipv4_object_groups", "ipv6_object_groups"
                                   ]

    @classmethod
    def match(cls, data_model):
        """
        function used by iac-validate
        """
        route_control = {}
        topology_switches = []
        switch_policy = []
        route_maps = []
        group_policies = []

        # Get route_control policies
        if data_model.get("vxlan", None):
            if data_model["vxlan"].get("overlay_extensions", None):
                if data_model["vxlan"].get("overlay_extensions").get("route_control", None):
                    route_control = data_model["vxlan"]["overlay_extensions"]["route_control"]
                    # Get groups policies
                    if data_model["vxlan"].get("overlay_extensions").get("route_control").get("groups", None):
                        group_policies = data_model["vxlan"]["overlay_extensions"]["route_control"]["groups"]
                    else:
                        # group is empty
                        return cls.results
                else:
                    # route control is empty
                    return cls.results

        # Get fabric switches
        if data_model.get("vxlan"):
            if data_model["vxlan"].get("topology"):
                if data_model.get("vxlan").get("topology").get("switches"):
                    topology_switches = (
                        data_model.get("vxlan").get("topology").get("switches")
                    )

        # Check switch Level
        if route_control.get("switches"):
            for switch_policy in route_control["switches"]:
                cls.check_switch_level(
                    switch_policy,
                    topology_switches,
                    group_policies
                )

        # Check groups integrity
        cls.check_groups(
            group_policies,
            route_control
        )

        # Check route maps integrity
        rm_keys = ['overlay_extensions', 'route_control', 'route_maps']
        check = cls.data_model_key_check(data_model["vxlan"], rm_keys)
        if 'route_maps' in check['keys_data']:
            route_maps = data_model["vxlan"]["overlay_extensions"]["route_control"]["route_maps"]
            cls.check_route_maps(route_maps)

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

        # Check if group in switch is defined in route_control group
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
        Check if group in switch is defined in route_control group
        """
        if list(filter(lambda group: group["name"] == switch_group, group_policies)):
            pass
        else:
            cls.results.append(
                f"vxlan.overlay_extensions.route_control.switches.groups.{switch_group} "
                "is not defined in vxlan.overlay_extensions.route_control.groups"
            )

    @classmethod
    def validate_unique_names(
        cls,
        route_control_object,
        label
    ):
        """
        Checks if route control object uses policy with unique name
        """

        # Track seen names
        seen_names = set()
        # Check for duplicates
        for policy in route_control_object:
            name = policy.get('name')
            if name in seen_names:
                cls.results.append(
                    "For vxlan.overlay_extensions.route_control." + label + name + " can be defined only one time")
            seen_names.add(name)

    @classmethod
    def validate_group_objects(
        cls,
        route_control_object,
        policy_name,
        route_control
    ):
        """
        Check if route_control_objects in group is defined in route_control
        """
        for policy in route_control_object:
            # The policy exist in the group. Check if exists under route control
            if route_control.get(policy_name, None):
                if list(filter(lambda group, policy=policy: group['name'] == policy['name'], route_control[policy_name])):
                    pass
                else:
                    cls.results.append(
                        f"vxlan.overlay_extensions.route_control.switches.groups.{policy_name}.{policy['name']} "
                        f"is not defined in vxlan.overlay_extensions.route_control.{policy_name}"
                    )
            else:
                cls.results.append(
                    f"vxlan.overlay_extensions.route_control.groups.{policy_name} "
                    "is not defined in vxlan.overlay_extensions.route_control"
                )

    @classmethod
    def check_groups(
        cls,
        group_policies,
        route_control
    ):
        """
        Check group policy integrity
        """
        for switch in group_policies:
            for policy_name in cls.route_control_objects_names:
                if switch.get(policy_name, None):
                    # Check uniquiness of route_control_object whitin a group
                    route_control_object = switch.get(policy_name)
                    cls.validate_unique_names(
                        route_control_object,
                        "groups." + switch["name"] + "." + policy_name + ".",
                    )

                    # Check if route_control_object in group is defined in route_control
                    cls.validate_group_objects(
                        route_control_object,
                        policy_name,
                        route_control
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
                for rm_set in seq_numer["set"]:
                    # Check set metric integrity
                    cls.check_set_metric_integrity(
                        rm_set
                    )

                    # Check set metric integrity
                    cls.check_set_next_hop_verify_availability(
                        rm_set
                    )

    @classmethod
    def check_set_next_hop_verify_availability(
        cls,
        rm_set,
    ):
        """
        Check if in the set_next_hop_verify_availability route map has next-hop ip defined
        """
        if rm_set.get("ipv4"):
            set_ip = rm_set["ipv4"]
            if 'next_hop' in set_ip:
                if 'verify_availability' in set_ip["next_hop"]:
                    if set_ip["next_hop"]['verify_availability']:
                        # Ip address should be defined in verify_availability
                        if 'address' not in set_ip["next_hop"]:
                            cls.results.append(
                                "For vxlan.overlay_extensions.route_control.route_maps.entries.set.ipv4.next_hop.verify_availability to be used, " +
                                "ipv4 address should be configured"
                            )
        if rm_set.get("ipv6"):
            set_ip = rm_set["ipv6"]
            if 'next_hop' in set_ip:
                if 'verify_availability' in set_ip["next_hop"]:
                    if set_ip["next_hop"]['verify_availability']:
                        # Ip address should be defined in verify_availability
                        if 'address' not in set_ip["next_hop"]:
                            cls.results.append(
                                "For vxlan.overlay_extensions.route_control.route_maps.entries.set.ipv6.next_hop.verify_availability to be used, " +
                                "ipv6 address should be configured"
                            )

    @classmethod
    def check_set_metric_integrity(
        cls,
        rm_set
    ):
        """
        Check if in the set_metric route map if we use metric bandwith or all the five metrics: bandwidth, delay, reliability, load, mtu
        """
        if rm_set.get("metric", None):
            set_metric = rm_set["metric"]
            metrics = ['bandwidth', 'delay', 'reliability', 'load', 'mtu']
            if 'bandwidth' in set_metric and len(set_metric) == 1:
                pass
            else:
                for metric in metrics:
                    if metric not in set_metric:
                        cls.results.append(
                            "For vxlan.overlay_extensions.route_control.route_maps.entries.set.metric to be enabled, " +
                            metric + " should be set in the metric.")

    @classmethod
    def data_model_key_check(cls, tested_object, keys):
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

    @classmethod
    def safeget(cls, dict, keys):
        # Utility function to safely get nested dictionary values
        for key in keys:
            if dict is None:
                return None
            if key in dict:
                dict = dict[key]
            else:
                return None

        return dict

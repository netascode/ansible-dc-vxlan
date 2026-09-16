# Copyright (c) 2024 Cisco Systems, Inc. and its affiliates
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# SPDX-License-Identifier: MIT

import json
import re
from jinja2 import ChainableUndefined, Environment, FileSystemLoader
from ansible_collections.ansible.utils.plugins.filter import ipaddr, hwaddr
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import hostname_to_ip_mapping, data_model_key_check


class PreparePlugin:
    """
    Class PreparePlugin
    """
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        """
        function to prepare data for route_control
        """
        templates_path = self.kwargs['templates_path']
        data_model = self.kwargs['results']['model_extended']
        default_values = self.kwargs['default_values']

        template_filename = "ndfc_route_control.j2"

        env = Environment(
            loader=FileSystemLoader(templates_path),
            undefined=ChainableUndefined,
            lstrip_blocks=True,
            trim_blocks=True,
        )

        env.filters["ipaddr"] = ipaddr.ipaddr
        env.filters["hwaddr"] = hwaddr.hwaddr
        template = env.get_template(template_filename)

        parent_keys = ['vxlan', 'overlay_extensions', 'route_control', 'route_maps']
        dm_check = data_model_key_check(data_model, parent_keys)

        # Check Route-Maps
        if 'route_maps' in dm_check['keys_data']:
            self.update_route_maps(data_model)

        # Check IPv4 ACL
        parent_keys = ['vxlan', 'overlay_extensions', 'route_control', 'ipv4_access_lists']
        dm_check = data_model_key_check(data_model, parent_keys)
        if 'ipv4_access_lists' in dm_check['keys_data']:
            for acl in data_model["vxlan"]["overlay_extensions"]["route_control"]["ipv4_access_lists"]:
                self.update_ip_access_lists(acl, 'ipv4')

        # Check IPv6 ACL
        parent_keys = ['vxlan', 'overlay_extensions', 'route_control', 'ipv6_access_lists']
        dm_check = data_model_key_check(data_model, parent_keys)
        if 'ipv6_access_lists' in dm_check['keys_data']:
            for acl in data_model["vxlan"]["overlay_extensions"]["route_control"]["ipv6_access_lists"]:
                self.update_ip_access_lists(acl, 'ipv6')

        parent_keys = ['vxlan', 'overlay_extensions', 'route_control']
        dm_check = data_model_key_check(data_model, parent_keys)
        if 'route_control' in dm_check['keys_data']:
            for route_control in data_model["vxlan"]["overlay_extensions"]["route_control"]:
                if "switches" == route_control:
                    for switch in data_model["vxlan"]["overlay_extensions"]["route_control"]["switches"]:
                        for sw_group in switch['groups']:
                            unique_name = f"route_control_{sw_group}"
                            group_policies = []
                            for group_name in data_model["vxlan"]["overlay_extensions"]["route_control"]["groups"]:
                                if sw_group == group_name["name"]:
                                    group_policies.append(group_name)

                            output = template.render(
                                data_model_extended=data_model,
                                item=data_model["vxlan"]["overlay_extensions"]["route_control"],
                                switch=switch['name'],
                                group_item=group_policies,
                                defaults=default_values)
                            has_legacy_config = any(
                                line.strip() and not line.lstrip().startswith("!")
                                for line in output.splitlines())

                            new_policies = self.build_native_policies(
                                group_policies,
                                data_model["vxlan"]["overlay_extensions"]["route_control"])
                            has_new_policies = bool(new_policies)
                            has_any_policy = has_legacy_config or has_new_policies

                            for new_policy_entry in new_policies:
                                if not any(policy['name'] == new_policy_entry['name']
                                           for policy in data_model["vxlan"]["policy"]["policies"]):
                                    data_model["vxlan"]["policy"]["policies"].append(new_policy_entry)

                            if has_legacy_config:
                                new_policy = {
                                    "name": unique_name,
                                    "template_name": "switch_freeform",
                                    "template_vars": {
                                        "CONF": output
                                    }
                                }
                                if not any(policy['name'] == unique_name for policy in data_model["vxlan"]["policy"]["policies"]):
                                    data_model["vxlan"]["policy"]["policies"].append(new_policy)

                            if any(sw['name'] == switch['name'] for sw in data_model["vxlan"]["policy"]["switches"]):
                                found_switch = next(([idx, i] for idx, i in enumerate(
                                    data_model["vxlan"]["policy"]["switches"]) if i["name"] == switch['name']))
                                if has_any_policy:
                                    if "groups" in found_switch[1].keys():
                                        if unique_name not in found_switch[1]["groups"]:
                                            data_model["vxlan"]["policy"]["switches"][found_switch[0]]["groups"].append(
                                                unique_name)
                                    else:
                                        data_model["vxlan"]["policy"]["switches"][found_switch[0]]["groups"] = [
                                            unique_name]
                            else:
                                new_switch = {
                                    "name": switch["name"],
                                    "groups": [unique_name]
                                }
                                if has_any_policy:
                                    data_model["vxlan"]["policy"]["switches"].append(new_switch)

                            if has_any_policy and not any(group['name'] == unique_name for group in data_model["vxlan"]["policy"]["groups"]):
                                new_group = {
                                    "name": unique_name,
                                    "policies": [],
                                    "priority": 500
                                }
                                if has_legacy_config:
                                    new_group["policies"].append({"name": unique_name})
                                new_group["policies"].extend(
                                    self._policy_ref(policy) for policy in new_policies)
                                data_model["vxlan"]["policy"]["groups"].append(new_group)
                            elif has_any_policy:
                                existing_group = next(
                                    group for group in data_model["vxlan"]["policy"]["groups"]
                                    if group["name"] == unique_name)
                                existing_policy_names = {
                                    policy["name"] for policy in existing_group.get("policies", [])}
                                existing_group.setdefault("policies", []).extend(
                                    self._policy_ref(policy)
                                    for policy in new_policies
                                    if policy["name"] not in existing_policy_names)

            data_model = hostname_to_ip_mapping(data_model)
        self.kwargs['results']['model_extended'] = data_model
        return self.kwargs['results']

    # Registry mapping route_control key -> builder method name.
    # Add a new entry (and matching method) for each new native NDFC template.
    NATIVE_BUILDERS = {
        "ipv4_prefix_lists": "build_ipv4_prefix_list_policies",
        "ipv4_access_lists": "build_ipv4_access_list_policies",
        "standard_community_lists": "build_standard_community_list_policies",
        "extended_community_lists": "build_extended_community_list_policies",
        # "ipv6_prefix_lists": "build_ipv6_prefix_list_policies",
        # "ipv6_access_lists": "build_ipv6_access_list_policies",
        # "route_maps": "build_route_map_policies",
        # ...
    }

    def build_native_policies(self, group_policies, route_control):
        """Dispatch to per-type builders and aggregate all native NDFC policies."""
        policies = []
        for _rc_key, builder_name in self.NATIVE_BUILDERS.items():
            builder = getattr(self, builder_name, None)
            if builder is None:
                continue
            policies.extend(builder(group_policies, route_control))
        return policies

    @staticmethod
    def _policy_ref(policy):
        ref = {"name": policy["name"]}
        if "priority" in policy:
            ref["priority"] = policy["priority"]
        return ref

    def build_ipv4_prefix_list_policies(self, group_policies, route_control):
        """Build NDFC ipv4_prefix_list policies for native definitions."""
        policies = []
        prefix_lists = {
            prefix_list["name"]: prefix_list
            for prefix_list in route_control.get("ipv4_prefix_lists", [])
        }
        for group in group_policies:
            for prefix_list_ref in group.get("ipv4_prefix_lists", []):
                prefix_list = prefix_lists.get(prefix_list_ref["name"])
                if not prefix_list or not prefix_list.get("native"):
                    continue
                entries = []
                for entry in prefix_list.get("entries", []):
                    entries.append({
                        "IP_MASK": str(entry["prefix"]),
                        "SEQ_NUM": str(entry["seq_number"]),
                        "ACTION": entry["operation"],
                        "EXACT_PREFIX_LEN": str(entry.get("eq", "")),
                        "MIN_PREFIX_LEN": str(entry.get("ge", "")),
                        "MAX_PREFIX_LEN": str(entry.get("le", "")),
                        "EXPLICIT_MASK": str(entry.get("mask", "")),
                    })
                policy = {
                    "name": prefix_list["name"],
                    "template_name": "ipv4_prefix_list",
                    "template_vars": {
                        "DESC": prefix_list.get("description", ""),
                        "PREFIX_LIST_NAME": prefix_list["name"],
                        "ENTRY_LIST": json.dumps(
                            {"ENTRY_LIST": entries}, separators=(",", ":"))
                    }
                }
                if "priority" in prefix_list_ref:
                    policy["priority"] = prefix_list_ref["priority"]
                policies.append(policy)
        return policies

    _PORT_OPERATOR_MAP = {
        "eq": "equal-to",
        "gt": "greater-than",
        "lt": "less-than",
        "neq": "not-equal-to",
        "range": "port-range",
    }

    @staticmethod
    def _wildcard_to_cidr(ip, wildcard):
        """Convert `ip + wildcard-mask` to CIDR notation.

        NDFC ip_acl template expects CIDR (e.g. 192.168.10.0/24) rather than
        the Cisco CLI `ip wildcard` form. Inverts the wildcard octets to a
        netmask, then normalizes via ansible.utils ipaddr filter.
        """
        try:
            netmask = ".".join(
                str(255 - int(octet)) for octet in str(wildcard).split("."))
            return ipaddr.ipaddr("{0}/{1}".format(ip, netmask), "subnet")
        except (ValueError, TypeError):
            return None

    @classmethod
    def _acl_endpoint_ip(cls, endpoint):
        """Render source/destination IP field for an ACL ACE payload."""
        if not endpoint:
            return ""
        if endpoint.get("any"):
            return "any"
        if endpoint.get("host"):
            return "{0}/32".format(endpoint["host"])
        if endpoint.get("ip"):
            wildcard = endpoint.get("wildcard")
            if wildcard:
                cidr = cls._wildcard_to_cidr(endpoint["ip"], wildcard)
                if cidr:
                    return cidr
            ip_str = str(endpoint["ip"])
            if "/" not in ip_str:
                return "{0}/32".format(ip_str)
            return ip_str
        return ""

    @classmethod
    def _acl_endpoint_port(cls, endpoint):
        """Return (port, action, range_start, range_end) for source/destination port."""
        if not endpoint or "port_number" not in endpoint:
            return "", "", "", ""
        port_number = endpoint["port_number"] or {}
        operator = port_number.get("operator", "")
        action = cls._PORT_OPERATOR_MAP.get(operator, "")
        if operator == "range":
            return (
                "",
                action,
                str(port_number.get("from", "")),
                str(port_number.get("to", "")),
            )
        port = port_number.get("port", "")
        return str(port) if port != "" else "", action, "", ""

    _ACL_PROTOCOL_ENUM = {"icmp", "ip", "tcp", "udp", "eigrp", "ospf", "pim", "igmp"}

    _ACL_PROTOCOL_TO_NUMERIC = {
        "ahp": "51",
        "esp": "50",
        "gre": "47",
        "nos": "94",
        "pcp": "108",
    }

    @classmethod
    def _acl_protocol(cls, protocol):
        """Return (PROTOCOL, CUSTOM_PROTOCOL) matching ND ip_acl template enum.

        ND ip_acl PROTOCOL is enum {icmp,ip,tcp,udp,eigrp,ospf,pim,igmp,custom}.
        Numeric or unsupported-keyword protocols must set PROTOCOL="custom" and
        CUSTOM_PROTOCOL to the IANA number. ahp/esp/gre/nos/pcp are in the
        schema but not in the ND enum, so they route through `custom`.
        """
        if isinstance(protocol, int):
            return "custom", str(protocol)
        protocol_str = str(protocol or "").strip()
        if not protocol_str:
            return "", ""
        if protocol_str in cls._ACL_PROTOCOL_ENUM:
            return protocol_str, ""
        if protocol_str in cls._ACL_PROTOCOL_TO_NUMERIC:
            return "custom", cls._ACL_PROTOCOL_TO_NUMERIC[protocol_str]
        return protocol_str, ""

    @staticmethod
    def _acl_tcp_advanced_option(entry):
        """Extract TCP advanced option flag (e.g. 'established') from filtering_options."""
        for opt in entry.get("filtering_options", []) or []:
            for flag in opt.get("flags", []) or []:
                if flag.get("establish"):
                    return "established"
        return ""

    def build_ipv4_access_list_policies(self, group_policies, route_control):
        """Build NDFC ip_acl policies for native ipv4_access_lists definitions.

        Verified against the ND `ip_acl` template (see
        route_control_native/ipv4_acl.md).

        Supported schema fields per entry (mapped to native ACES payload):
          - seq_number, operation (permit/deny), remark
          - protocol:
            - ND enum keywords: icmp, ip, tcp, udp, eigrp, ospf, pim, igmp
            - schema-only keywords ahp/esp/gre/nos/pcp -> emitted as
              PROTOCOL=custom + CUSTOM_PROTOCOL=<IANA number>
            - numeric (0-255) -> PROTOCOL=custom + CUSTOM_PROTOCOL=<n>
          - source/destination: any, host (rendered X/32), ip (bare -> X/32),
            ip + wildcard (converted to CIDR)
          - source/destination.port_number: operator (eq/neq/gt/lt/range),
            port, from, to (only applies when PROTOCOL in tcp/udp/custom per
            ND `IsShow` guards)
          - filtering_options.flags: established, ack, fin, psh, rst, syn, urg
            -> TCP_ADVANCED_OPTION (ND enum: ack, fin, established, psh, rst,
            syn — accepts only one; first match wins)

        NOT mapped by this builder — keep `native: false` (or omit) and use
        the Jinja freeform path when any of these are needed:
          - ACL-level: statistics_per_entry, fragments, ignore_routable
          - filtering_options: dscp, precedence, ttl, packet_length,
            time_range, http_method, tcp_option_length, tcp_flags_mask,
            udf, load_share, fragments, set_erspan_dscp, set_erspan_gre_proto
          - entry-level: log
          - ICMP advanced options (ND template has an ICMP_ADVANCED_OPTION
            enum but no schema field maps to it — ICMP_ADVANCED_OPTION is
            always emitted as "")
          - source/destination.addrgroup (requires ipv4_object_groups linkage,
            not supported by the native ip_acl template)

        The freeform path (ndfc_route_control_access_list_ipv4.j2) already
        renders all of the above via `switch_freeform`.
        """
        policies = []
        access_lists = {
            acl["name"]: acl
            for acl in route_control.get("ipv4_access_lists", [])
        }
        for group in group_policies:
            for acl_ref in group.get("ipv4_access_lists", []):
                acl = access_lists.get(acl_ref["name"])
                if not acl or not acl.get("native"):
                    continue
                aces = []
                for entry in acl.get("entries", []):
                    if entry.get("remark"):
                        ace = {
                            "ACTION": "remark",
                            "SEQUENCE_NUMBER": str(entry["seq_number"]),
                            "CUSTOM_PROTOCOL": "",
                            "SRC_IP": "",
                            "SRC_PORT": "",
                            "DEST_IP": "",
                            "DEST_PORT": "",
                            "REMARK_COMMENT": entry["remark"],
                            "ICMP_ADVANCED_OPTION": "",
                            "TCP_ADVANCED_OPTION": "",
                            "SRC_PORT_RANGE_START": "",
                            "SRC_PORT_RANGE_END": "",
                            "DEST_PORT_RANGE_START": "",
                            "DEST_PORT_RANGE_END": "",
                            "SRC_PORT_ACTION": "",
                            "DEST_PORT_ACTION": "",
                            "PROTOCOL": "",
                        }
                        aces.append(ace)
                        continue

                    protocol = entry.get("protocol", "")
                    protocol_value, custom_protocol = self._acl_protocol(protocol)

                    src_port, src_action, src_from, src_to = self._acl_endpoint_port(
                        entry.get("source"))
                    dst_port, dst_action, dst_from, dst_to = self._acl_endpoint_port(
                        entry.get("destination"))

                    ace = {
                        "ACTION": entry.get("operation", ""),
                        "SEQUENCE_NUMBER": str(entry["seq_number"]),
                        "CUSTOM_PROTOCOL": custom_protocol,
                        "SRC_IP": self._acl_endpoint_ip(entry.get("source")),
                        "SRC_PORT": src_port,
                        "DEST_IP": self._acl_endpoint_ip(entry.get("destination")),
                        "DEST_PORT": dst_port,
                        "REMARK_COMMENT": "",
                        "ICMP_ADVANCED_OPTION": "",
                        "TCP_ADVANCED_OPTION": self._acl_tcp_advanced_option(entry),
                        "SRC_PORT_RANGE_START": src_from,
                        "SRC_PORT_RANGE_END": src_to,
                        "DEST_PORT_RANGE_START": dst_from,
                        "DEST_PORT_RANGE_END": dst_to,
                        "PROTOCOL": protocol_value,
                        "SRC_PORT_ACTION": src_action,
                        "DEST_PORT_ACTION": dst_action,
                    }
                    aces.append(ace)

                policy = {
                    "name": acl["name"],
                    "template_name": "ip_acl",
                    "template_vars": {
                        "DESC": acl.get("description", ""),
                        "ACL_NAME": acl["name"],
                        "ACES": json.dumps(
                            {"ACES": aces}, separators=(",", ":"))
                    }
                }
                if "priority" in acl_ref:
                    policy["priority"] = acl_ref["priority"]
                policies.append(policy)
        return policies

    _COMMUNITY_WELL_KNOWN_MAP = {
        "blackhole": "blackhole",
        "graceful-shutdown": "gracefulShutdown",
        "internet": "internet",
        "local-as": "localAsn",
        "no-advertise": "noAdvertise",
        "no-export": "noExport",
    }

    @classmethod
    def _split_community_entry(cls, communities):
        """Split schema `communities` list into (well_known_flags_dict, community_numbers_str).

        Schema allows two kinds of items per entry:
          - `ASN:NN` regex values -> concatenated into comma-separated communityNumbers
          - well-known keywords (blackhole, graceful-shutdown, internet, local-as,
            no-advertise, no-export) -> mapped to individual NDFC boolean fields.

        NDFC template stores every boolean as "true"/"" string, never Python bool.
        """
        flags = {ndfc_key: "" for ndfc_key in cls._COMMUNITY_WELL_KNOWN_MAP.values()}
        numbers = []
        for community in communities or []:
            if community in cls._COMMUNITY_WELL_KNOWN_MAP:
                flags[cls._COMMUNITY_WELL_KNOWN_MAP[community]] = "true"
            else:
                numbers.append(str(community))
        return flags, ",".join(numbers)

    def build_standard_community_list_policies(self, group_policies, route_control):
        """Build NDFC community_list policies for native standard_community_lists."""
        policies = []
        community_lists = {
            community_list["name"]: community_list
            for community_list in route_control.get("standard_community_lists", [])
        }
        for group in group_policies:
            for community_list_ref in group.get("standard_community_lists", []):
                community_list = community_lists.get(community_list_ref["name"])
                if not community_list or not community_list.get("native"):
                    continue
                entries = []
                for entry in community_list.get("entries", []):
                    flags, community_numbers = self._split_community_entry(
                        entry.get("communities", []))
                    entries.append({
                        "sequenceNumber": str(entry["seq_number"]),
                        "action": entry["operation"],
                        "blackhole": flags["blackhole"],
                        "gracefulShutdown": flags["gracefulShutdown"],
                        "internet": flags["internet"],
                        "localAsn": flags["localAsn"],
                        "noAdvertise": flags["noAdvertise"],
                        "noExport": flags["noExport"],
                        "communityNumbers": community_numbers,
                    })
                policy = {
                    "name": community_list["name"],
                    "template_name": "community_list",
                    "template_vars": {
                        "comListName": community_list["name"],
                        "type": "standard",
                        "expandedCommunityListEntries": "",
                        "standardCommunityListEntries": json.dumps(
                            {"standardCommunityListEntries": entries},
                            separators=(",", ":")),
                    },
                }
                if "priority" in community_list_ref:
                    policy["priority"] = community_list_ref["priority"]
                policies.append(policy)
        return policies

    @staticmethod
    def _build_extended_collections(communities):
        """Split schema `communities` dict into NDFC extended-community collections.

        Schema fields per entry.communities:
          - rt: list -> comma-joined into routeTargetCollection
          - soo: list -> comma-joined into siteOfOriginCollection
          - rmac: list -> comma-joined into routerMacCollection
          - 4byteas_generic: list of {transitive: bool, extended_community_number_list}
            split by `transitive` flag into transitive/nonTransitive Generic collections.

        NDFC template expects comma-separated strings (e.g. "65535:40, 65535:60"),
        matching the reference payload format.
        """
        communities = communities or {}

        rt_str = ", ".join(str(item) for item in communities.get("rt", []) or [])
        soo_str = ", ".join(str(item) for item in communities.get("soo", []) or [])
        rmac_str = ", ".join(str(item) for item in communities.get("rmac", []) or [])

        transitive = []
        non_transitive = []
        for gen in communities.get("4byteas_generic", []) or []:
            community_number = str(gen.get("extended_community_number_list", ""))
            if not community_number:
                continue
            if gen.get("transitive"):
                transitive.append(community_number)
            else:
                non_transitive.append(community_number)

        return {
            "routeTargetCollection": rt_str,
            "siteOfOriginCollection": soo_str,
            "routerMacCollection": rmac_str,
            "transitiveGenericExtendedCollection": ", ".join(transitive),
            "nonTransitiveGenericExtendedCollection": ", ".join(non_transitive),
        }

    def build_extended_community_list_policies(self, group_policies, route_control):
        """Build NDFC extended_community_list policies for native definitions."""
        policies = []
        community_lists = {
            community_list["name"]: community_list
            for community_list in route_control.get("extended_community_lists", [])
        }
        for group in group_policies:
            for community_list_ref in group.get("extended_community_lists", []):
                community_list = community_lists.get(community_list_ref["name"])
                if not community_list or not community_list.get("native"):
                    continue
                entries = []
                for entry in community_list.get("entries", []):
                    collections = self._build_extended_collections(
                        entry.get("communities"))
                    entries.append({
                        "sequenceNumber": str(entry["seq_number"]),
                        "action": entry["operation"],
                        "routerMacCollection": collections["routerMacCollection"],
                        "routeTargetCollection": collections["routeTargetCollection"],
                        "siteOfOriginCollection": collections["siteOfOriginCollection"],
                        "transitiveGenericExtendedCollection":
                            collections["transitiveGenericExtendedCollection"],
                        "nonTransitiveGenericExtendedCollection":
                            collections["nonTransitiveGenericExtendedCollection"],
                    })
                policy = {
                    "name": community_list["name"],
                    "template_name": "extended_community_list",
                    "template_vars": {
                        "extCommunityListName": community_list["name"],
                        "type": "standard",
                        "expandedEntries": "",
                        "standardEntries": json.dumps(
                            {"standardEntries": entries},
                            separators=(",", ":")),
                    },
                }
                if "priority" in community_list_ref:
                    policy["priority"] = community_list_ref["priority"]
                policies.append(policy)
        return policies

    def update_route_maps(self, data_model):
        """function to rewrite parameters in route_maps"""
        for route_map in data_model["vxlan"]["overlay_extensions"]["route_control"]["route_maps"]:
            if "entries" in route_map:
                for entry in route_map["entries"]:
                    if "match" in entry:
                        for option_match in entry["match"]:
                            # Rewrite match interface based on CLI
                            # Order is not important, only the case
                            # Example: CLI match interface Ethernet1/10 loopback100 Null0 port-channel100
                            if "interface" in option_match:
                                option_match["interface"] = self.rewrite_match_interface(
                                    option_match["interface"])
                    if "set" in entry:
                        for option_set in entry["set"]:
                            # Rewrite route-map IP Precedence number to string
                            # Example: set ip precedence 6 -> set ip precedence internet
                            precedence_translation = {
                                0: 'routine',
                                1: 'priority',
                                2: 'immediate',
                                3: 'flash',
                                4: 'flash-override',
                                5: 'critical',
                                6: 'internet',
                                7: 'network',
                            }
                            if ("ipv4" in option_set) and ("precedence" in option_set["ipv4"]):
                                if isinstance(option_set["ipv4"]["precedence"], int):
                                    option_set["ipv4"]["precedence"] = precedence_translation[
                                        option_set["ipv4"]["precedence"]]

                            if ("ipv6" in option_set) and ("precedence" in option_set["ipv6"]):
                                if isinstance(option_set["ipv6"]["precedence"], int):
                                    option_set["ipv6"]["precedence"] = precedence_translation[
                                        option_set["ipv6"]["precedence"]]

    def update_ip_access_lists(self, acl, ip_version):
        """
        function to rewrite parameters in IP ACLs
        """
        if "entries" in acl:
            for entry in acl["entries"]:
                if ("protocol" in entry) and (entry["protocol"] in ['tcp', 'udp', 'icmp']):
                    if ip_version == 'ipv6' and entry['protocol'] == 'icmp':
                        proto = 'icmp6'
                    else:
                        proto = entry['protocol']

                    if "source" in entry and "port_number" in entry["source"]:

                        if "port" in entry["source"]["port_number"]:
                            entry["source"][
                                "port_number"]["port"] = self.update_port_number(
                                entry["source"]["port_number"]["port"], proto)
                        if "from" in entry["source"]["port_number"]:
                            entry["source"][
                                "port_number"]["from"] = self.update_port_number(
                                entry["source"]["port_number"]["from"], proto)
                        if "to" in entry["source"]["port_number"]:
                            entry["source"][
                                "port_number"]["to"] = self.update_port_number(
                                entry["source"]["port_number"]["to"], proto)
                    if "destination" in entry and "port_number" in entry["destination"]:
                        if "port" in entry["destination"]["port_number"]:
                            entry["destination"][
                                "port_number"]["port"] = self.update_port_number(
                                entry["destination"]["port_number"]["port"], proto)
                        if "from" in entry["destination"]["port_number"]:
                            entry["destination"][
                                "port_number"]["from"] = self.update_port_number(
                                entry["destination"]["port_number"]["from"], proto)
                        if "to" in entry["destination"]["port_number"]:
                            entry["destination"][
                                "port_number"]["to"] = self.update_port_number(
                                entry["destination"]["port_number"]["to"], proto)

    def update_port_number(self, port_number, protocol):
        """
        Convert TCP, UDP port number with well-know
        """

        tcp = {
            7: "echo",
            9: "discard",
            13: "daytime",
            19: "chargen",
            20: "ftp-data",
            21: "ftp",
            23: "telnet",
            25: "smtp",
            37: "time",
            43: "whois",
            49: "tacacs",
            53: "domain",
            70: "gopher",
            79: "finger",
            80: "www",
            101: "hostname",
            109: "pop2",
            110: "pop3",
            111: "sunrpc",
            113: "ident",
            119: "nntp",
            179: "bgp",
            194: "irc",
            496: "pim-auto-rp",
            512: "exec",
            513: "login",
            514: "cmd",
            515: "lpd",
            517: "talk",
            540: "uucp",
            543: "klogin",
            544: "kshell",
            3949: "drip",
        }

        udp = {
            7: "echo",
            9: "discard",
            37: "time",
            42: "nameserver",
            49: "tacacs",
            53: "domain",
            67: "bootps",
            68: "bootpc",
            69: "tftp",
            111: "sunrpc",
            123: "ntp",
            137: "netbios-ns",
            138: "netbios-dgm",
            139: "netbios-ss",
            161: "snmp",
            162: "snmptrap",
            177: "xdmcp",
            195: "dnsix",
            434: "mobile-ip",
            496: "pim-auto-rp",
            500: "isakmp",
            512: "biff",
            513: "who",
            514: "syslog",
            517: "talk",
            520: "rip",
            4500: "non500-isakmp",
        }

        icmp = {
            0: "echo-reply",
            3: "unreachable",
            4: "source-quench",
            5: "redirect",
            6: "alternate-address",
            8: "echo",
            9: "router-advertisement",
            10: "router-solicitation",
            11: "time-exceeded",
            12: "parameter-problem",
            13: "timestamp-request",
            14: "timestamp-reply",
            15: "information-request",
            16: "information-reply",
            17: "mask-request",
            18: "mask-reply",
            30: "traceroute",
            31: "conversion-error",
            32: "mobile-redirect",
        }

        icmp6 = {
            1: "unreachable",
            2: "packet-too-big",
            3: "time-exceeded",
            4: "parameter-problem",
            128: "echo-request",
            129: "echo-reply",
            130: "mld-query",
            131: "mld-report",
            132: "mld-reduction",
            133: "router-solicitation",
            134: "router-advertisement",
            135: "nd-ns",
            136: "nd-na",
            137: "redirect",
            138: "router-renumbering",
            143: "mldv2",
        }

        if protocol == 'tcp':
            if port_number in tcp:
                return tcp[port_number]

        elif protocol == 'udp':
            if port_number in udp:
                return udp[port_number]

        elif protocol == 'icmp':
            if port_number in icmp:
                return icmp[port_number]

        elif protocol == 'icmp6':
            if port_number in icmp6:
                return icmp6[port_number]

        return port_number

    def rewrite_match_interface(self, interfaces):
        """
        Rewrite interface with proper case and name
        """
        new_interfaces = []
        for interface in interfaces:
            intf_ethernet = re.match(r'(?i)^(?:e|eth(?:ernet)?)(\d(?:\/\d+){1,2}$)', interface)
            intf_ethernetdot1q = re.match(r'(?i)^(?:e|eth(?:ernet)?)(\d(?:\/\d+){1,2}.(\d+)$)', interface)
            intf_loopback = re.match(r'(?i)^(?:lo|lo(?:opback)?)(\d+)$', interface)
            intf_portchannel = re.match(r'(?i)^(?:po|po(?:rt-channel)?)(\d+)$', interface)
            intf_portchanneldot1q = re.match(r'(?i)^(?:po|po(?:ort-channel)?)(\d{1,4}.\d+)$', interface)
            intf_null = re.match(r'(?i)^(?:n|null:?)([0])$', interface)
            if intf_ethernet:
                new_interfaces.append("Ethernet" + intf_ethernet[1])
            elif intf_ethernetdot1q:
                new_interfaces.append("Ethernet" + intf_ethernetdot1q[1])
            elif intf_loopback:
                new_interfaces.append("loopback" + intf_loopback[1])
            elif intf_portchannel:
                new_interfaces.append("port-channel" + intf_portchannel[1])
            elif intf_portchanneldot1q:
                new_interfaces.append("port-channel" + intf_portchanneldot1q[1])
            elif intf_null:
                new_interfaces.append("Null" + intf_null[1])
        return new_interfaces

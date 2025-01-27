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

import re
from jinja2 import ChainableUndefined, Environment, FileSystemLoader
from ansible_collections.ansible.utils.plugins.filter import ipaddr, hwaddr
from ....plugin_utils.helper_functions import hostname_to_ip_mapping, data_model_key_check


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
        model_data = self.kwargs['results']['model_extended']
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
        dm_check = data_model_key_check(model_data, parent_keys)

        # Check Route-Maps
        if 'route_maps' in dm_check['keys_data']:
            self.update_route_maps(model_data)

        # Check IPv4 ACL
        parent_keys = ['vxlan', 'overlay_extensions', 'route_control', 'ipv4_access_lists']
        dm_check = data_model_key_check(model_data, parent_keys)
        if 'ipv4_access_lists' in dm_check['keys_data']:
            for acl in model_data["vxlan"]["overlay_extensions"]["route_control"]["ipv4_access_lists"]:
                self.update_ip_access_lists(acl, 'ipv4')

        # Check IPv6 ACL
        parent_keys = ['vxlan', 'overlay_extensions', 'route_control', 'ipv6_access_lists']
        dm_check = data_model_key_check(model_data, parent_keys)
        if 'ipv6_access_lists' in dm_check['keys_data']:
            for acl in model_data["vxlan"]["overlay_extensions"]["route_control"]["ipv6_access_lists"]:
                self.update_ip_access_lists(acl, 'ipv6')

        parent_keys = ['vxlan', 'overlay_extensions', 'route_control']
        dm_check = data_model_key_check(model_data, parent_keys)
        if 'route_control' in dm_check['keys_data']:
            for route_control in model_data["vxlan"]["overlay_extensions"]["route_control"]:
                if "switches" == route_control:
                    for switch in model_data["vxlan"]["overlay_extensions"]["route_control"]["switches"]:
                        for sw_group in switch['groups']:
                            unique_name = f"route_control_{sw_group}"
                            group_policies = []
                            for group_name in model_data["vxlan"]["overlay_extensions"]["route_control"]["groups"]:
                                if sw_group == group_name["name"]:
                                    group_policies.append(group_name)

                            output = template.render(
                                MD_Extended=model_data,
                                item=model_data["vxlan"]["overlay_extensions"]["route_control"],
                                switch=switch['name'],
                                group_item=group_policies,
                                defaults=default_values)

                            new_policy = {
                                "name": unique_name,
                                "template_name": "switch_freeform",
                                "template_vars": {
                                    "CONF": output
                                }
                            }

                            model_data["vxlan"]["policy"]["policies"].append(new_policy)

                            if any(sw['name'] == switch['name'] for sw in model_data["vxlan"]["policy"]["switches"]):
                                found_switch = next(([idx, i] for idx, i in enumerate(
                                    model_data["vxlan"]["policy"]["switches"]) if i["name"] == switch['name']))
                                if "groups" in found_switch[1].keys():
                                    model_data["vxlan"]["policy"]["switches"][found_switch[0]]["groups"].append(
                                        unique_name)
                                else:
                                    model_data["vxlan"]["policy"]["switches"][found_switch[0]]["groups"] = [
                                        unique_name]
                            else:
                                new_switch = {
                                    "name": switch["name"],
                                    "groups": [unique_name]
                                }
                                model_data["vxlan"]["policy"]["switches"].append(new_switch)

                            if not any(group['name'] == sw_group for group in model_data["vxlan"]["policy"]["groups"]):
                                new_group = {
                                    "name": unique_name,
                                    "policies": [
                                        {"name": unique_name},
                                    ],
                                    "priority": 500
                                }
                                model_data["vxlan"]["policy"]["groups"].append(new_group)

            model_data = hostname_to_ip_mapping(model_data)
        self.kwargs['results']['model_extended'] = model_data
        return self.kwargs['results']

    def update_route_maps(self, model_data):
        """function to rewrite parameters in route_maps"""
        for route_map in model_data["vxlan"]["overlay_extensions"]["route_control"]["route_maps"]:
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

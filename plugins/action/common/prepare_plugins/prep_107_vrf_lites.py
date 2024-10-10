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

from jinja2 import ChainableUndefined, Environment, FileSystemLoader
from ...helper_functions import hostname_to_ip_mapping
from ansible_collections.ansible.utils.plugins.filter import ipaddr


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        templates_path = self.kwargs['templates_path']
        model_data = self.kwargs['results']['model_extended']
        default_values = self.kwargs['default_values']        

        template_filename = "ndfc_vrf_lite.j2"

        env = Environment(
            loader=FileSystemLoader(templates_path),
            undefined=ChainableUndefined,
            lstrip_blocks=True,
            trim_blocks=True,
        )

        env.filters["ipaddr"] = ipaddr.ipaddr
        template = env.get_template(template_filename)

        for vrf_lite in model_data["vxlan"]["overlay_extensions"]["vrf_lites"]:
            ospf_enabled = True if vrf_lite.get(
                "ospf") is not None else False
            default_area = vrf_lite.get("ospf", {}).get(
                "default_area",
                default_values["vxlan"]["overlay_extensions"]["vrf_lites"]["ospf"]["default_area"]
            )
            for switch in vrf_lite["switches"]:
                unique_name = f"nac_{vrf_lite['name']}_{switch['name']}"

                # Adding redistribution secion under the switches with the vrf_lite global config if it is not defined
                # for example:
                # before:
                # vxlan:
                #   overlay_extensions:
                #     vrf_lites:
                #       - name: ospf_vrf_red
                #         vrf: vrf_red
                #         redistribution:
                #           - source: direct
                #             route_map: fabric-rmp-redist-direct
                #           - source: static
                #             route_map: fabric-rmp-redist-static
                #         switches:
                #           - name: dc-border1
                # after:
                # vxlan:
                #   overlay_extensions:
                #     vrf_lites:
                #       - name: ospf_vrf_red
                #         vrf: vrf_red
                #         redistribution:
                #           - source: direct
                #             route_map: fabric-rmp-redist-direct
                #           - source: static
                #             route_map: fabric-rmp-redist-static
                #         switches:
                #           - name: dc-border1
                #             redistribution:
                #               - source: direct
                #                 route_map: fabric-rmp-redist-direct
                #               - source: static
                #                 route_map: fabric-rmp-redist-static

                g_redist = vrf_lite.get("redistribution", [])
                if switch.get("redistribution", []) == []:
                    switch["redistribution"] = g_redist

                # Adding ospf section under the interfaces config if ospf is not define with the default area id
                # for example:
                # before:
                # vxlan:
                #   overlay_extensions:
                #     vrf_lites:
                #       - name: ospf_vrf_red
                #         vrf: vrf_red
                #         ospf:
                #           process: overlay
                #           default_area: 0
                #         switches:
                #           - name: dc-border1
                #             interfaces:
                #               - name: ethernet1/1
                #                 ospf:
                #                   area: 1
                #               - name: ethernet1/2
                #               - name: ethernet1/3
                #                 ospf:
                #                   area_cost: 55
                # after:
                # vxlan:
                #   overlay_extensions:
                #     vrf_lites:
                #       - name: ospf_vrf_red
                #         vrf: vrf_red
                #         ospf:
                #           process: overlay
                #           default_area: 0
                #         switches:
                #           - name: dc-border1
                #             interfaces:
                #               - name: ethernet1/1
                #                 ospf:
                #                   area: 1
                #               - name: ethernet1/2
                #                 ospf:
                #                   area: 0
                #               - name: ethernet1/3
                #                 ospf:
                #                   area: 0
                #                   area_cost: 55

                for intf_index in range(len(switch.get("interfaces", []))):
                    intf = switch["interfaces"][intf_index]
                    if not ospf_enabled or (intf.get("ospf") is not None and intf["ospf"].get("area", -1) != -1):
                        continue
                    if intf.get("ospf") is None:
                        intf["ospf"] = {
                            "area": default_area
                        }
                    else:
                        intf["ospf"]["area"] = default_area
                    switch["interfaces"][intf_index] = intf

                # Adding address_family_ipv4_unicast and address_family_ipv6_unicast and child keys
                # under switches with the vrf_lite global config if it is not defined.
                # for example:
                # before:
                # vxlan:
                #   overlay_extensions:
                #     vrf_lites:
                #       - name: myvrf_50001_vrf_lite
                #         vrf: myvrf_50001
                #         bgp:
                #           local_as: 1111
                #           address_family_ipv4_unicast:
                #               additional_paths_receive: true
                #               additional_paths_send: true
                #               additional_paths_selection_route_map: test-map-globalaf4
                #               default_originate: true
                #               ebgp_distance: 25
                #               ibgp_distance: 180
                #               local_distance: 200
                #           address_family_ipv6_unicast:
                #               additional_paths_receive: true
                #               additional_paths_send: true
                #               additional_paths_selection_route_map: test-map-globalaf6
                #               default_originate: true
                #               ebgp_distance: 25
                #               ibgp_distance: 180
                #               local_distance: 200
                #         switches:
                #           - name: netascode4-ebgp-bl1
                #             bgp:
                #               local_as: 1111
                # after:
                # vxlan:
                #   overlay_extensions:
                #     vrf_lites:
                #       - name: myvrf_50001_vrf_lite
                #         vrf: myvrf_50001
                #         bgp:
                #           local_as: 1111
                #           address_family_ipv4_unicast:
                #               additional_paths_receive: true
                #               additional_paths_send: true
                #               additional_paths_selection_route_map: test-map-globalaf4
                #               default_originate: true
                #               ebgp_distance: 25
                #               ibgp_distance: 180
                #               local_distance: 200
                #           address_family_ipv6_unicast:
                #               additional_paths_receive: true
                #               additional_paths_send: true
                #               additional_paths_selection_route_map: test-map-globalaf6
                #               default_originate: true
                #               ebgp_distance: 25
                #               ibgp_distance: 180
                #               local_distance: 200
                #         switches:
                #           - name: netascode4-ebgp-bl1
                #             bgp:
                #               local_as: 1111
                #               address_family_ipv4_unicast:
                #                   additional_paths_receive: true
                #                   additional_paths_send: true
                #                   additional_paths_selection_route_map: test-map-globalaf4
                #                   default_originate: true
                #                   ebgp_distance: 25
                #                   ibgp_distance: 180
                #                   local_distance: 200
                #               address_family_ipv6_unicast:
                #                   additional_paths_receive: true
                #                   additional_paths_send: true
                #                   additional_paths_selection_route_map: test-map-globalaf6
                #                   default_originate: true
                #                   ebgp_distance: 25
                #                   ibgp_distance: 180
                #                   local_distance: 200
                if "bgp" in vrf_lite:
                    for af in ["address_family_ipv4_unicast", "address_family_ipv6_unicast"]:
                        if af in vrf_lite["bgp"]:
                            switch_bgp_af = switch.setdefault("bgp", {}).setdefault(af, {})
                            for key, value in vrf_lite["bgp"][af].items():
                                if key not in switch_bgp_af:
                                    switch_bgp_af[key] = value

                output = template.render(
                    MD_Extended=model_data, item=vrf_lite, switch_item=switch, defaults=default_values)

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
                    model_data["vxlan"]["policy"]["switches"].append(
                        new_switch)

                if not any(group['name'] == vrf_lite['name'] for group in model_data["vxlan"]["policy"]["groups"]):
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

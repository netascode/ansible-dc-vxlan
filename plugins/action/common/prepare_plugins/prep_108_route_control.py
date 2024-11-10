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
from ....plugin_utils.helper_functions import hostname_to_ip_mapping
from ansible_collections.ansible.utils.plugins.filter import ipaddr


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
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
        template = env.get_template(template_filename)

        if "overlay_extensions" in model_data["vxlan"]:
            if "route_control" in model_data["vxlan"]["overlay_extensions"]:
                for route_control in model_data["vxlan"]["overlay_extensions"]["route_control"]:
                    if "switches" == route_control:
                        for switch in model_data["vxlan"]["overlay_extensions"]["route_control"]["switches"]:
                        # for switch in route_control["switches"]:
                            unique_name = f"nac_{switch['name']}_route_control"
                            # unique_name = f"nac_{route_control['name']}_{switch['name']}_route_control"
                            output = template.render(
                                # MD_Extended=model_data, item=route_control, switch_item=switch, defaults=default_values)
                                MD_Extended=model_data, item=model_data["vxlan"]["overlay_extensions"]["route_control"], group=model_data["vxlan"]["overlay_extensions"]["route_control"]["groups"], switch_item=switch, defaults=default_values)

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

                            if not any(group['name'] == route_control['name'] for group in model_data["vxlan"]["policy"]["groups"]):
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

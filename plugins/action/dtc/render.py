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

from __future__ import absolute_import, division, print_function


__metaclass__ = type

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase

from jinja2 import ChainableUndefined, Environment, FileSystemLoader


display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False
        results['msg'] = None
        results['data'] = {}

        data = self._task.args.get('data')
        iterable = self._task.args.get('iterable')
        templates_path = self._task.args.get('templates_path')
        template_filename = self._task.args.get('template_filename')

        env = Environment(
            loader=FileSystemLoader(templates_path),
            undefined=ChainableUndefined,
            lstrip_blocks=True,
            trim_blocks=True,
        )

        # import epdb; epdb.st()

        template = env.get_template(template_filename)

        for item in iterable:
            for switch in item['switches']:
                new_policy = {}

                output = template.render(MD_Extended=data, item=item, switch_item=switch)

                new_policy = {
                    "name": f"{item['name']}_{switch['name']}",
                    "template_name": "switch_freeform",
                    "template_vars": {
                        "CONF": output
                    }
                }

                data["vxlan"]["policy"]["policies"].append(new_policy)

                new_switch = {}
                if any(sw['name'] == switch['name'] for sw in data["vxlan"]["policy"]["switches"]):
                    found_switch = next(([idx, i] for idx, i in enumerate(data["vxlan"]["policy"]["switches"]) if i["name"] == switch['name']))
                    if "groups" in found_switch[1].keys():
                        data["vxlan"]["policy"]["switches"][found_switch[0]]["groups"].append(f"{item['name']}_{switch['name']}")
                    else:
                        data["vxlan"]["policy"]["switches"][found_switch[0]]["groups"] = [f"{item['name']}_{switch['name']}"]
                else:
                    new_switch = {
                        "name": switch["name"],
                        "groups": [f"{item['name']}_{switch['name']}"]
                    }
                    data["vxlan"]["policy"]["switches"].append(new_switch)

                new_group = {}
                if not any(group['name'] == item['name'] for group in data["vxlan"]["policy"]["groups"]):
                    new_group = {
                        "name": f"{item['name']}_{switch['name']}",
                        "policies": [
                            {"name": f"{item['name']}_{switch['name']}"},
                        ],
                        "priority": 500
                    }
                    data["vxlan"]["policy"]["groups"].append(new_group)

        results['data'] = data
        return results

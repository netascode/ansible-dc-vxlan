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

from ansible.plugins.action import ActionBase
import json


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['poap_data'] = {}

        model_data = self._task.args["model_data"]
        fabric_name = model_data['vxlan']['global']['name']
        switches = model_data['vxlan']['topology']['switches']

        poap_supported_switches = False
        for switch in switches:
            if 'poap' in switch and switch['poap'].get('bootstrap'):
                poap_supported_switches = True

        if not poap_supported_switches:
            return results

        if poap_supported_switches:
            fabric_name = 'nac-ndfc1'
            poap_data = self._execute_module(
                module_name="cisco.dcnm.dcnm_rest",
                module_args={
                    "method": "GET",
                    "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/{fabric_name}/inventory/poap"
                },
                task_vars=task_vars,
                tmp=tmp
            )

            if poap_data['response']['RETURN_CODE'] == 200:
                parsed_data = self._parse_poap_data(poap_data['response']['DATA'])

        if parsed_data:
            results['poap_data'] = parsed_data


        return results

    def _parse_poap_data(self, poap_data):
        # Helper function to parse the following data into a dict strucuture keyed on serial number
        #
        # [{'data': '{"gateway": "10.15.9.1/24", "modulesModel": ["N9K-X9364v", "N9K-vSUP"]}',
        #   'fingerprint': 'MD5:eb:c9:87:d9:13:8a:5d:06:04:0e:23:c8:a5:8c:d2:77',
        #   'model': 'N9K-C9300v',
        #   'publicKey': 'ssh-rsa AAAAB3<snip>',
        #   'reAdd': False,
        #   'seedSwitchFlag': False,
        #   'serialNumber': '9Y0K4YPFV64',
        #   'version': '9.3(8)'}]
        #

        parsed_poap_data = {}
        for switch in poap_data:
            parsed_poap_data[switch['serialNumber']] = {}
            parsed_poap_data[switch['serialNumber']]['model'] = switch['model']
            parsed_poap_data[switch['serialNumber']]['version'] = switch['version']
            parsed_poap_data[switch['serialNumber']]['gateway'] = self._split_string_data(switch['data'])['gateway']
            parsed_poap_data[switch['serialNumber']]['modulesModel'] = self._split_string_data(switch['data'])['modulesModel']
            parsed_poap_data[switch['serialNumber']]['serialNumber'] = switch['serialNumber']


        return parsed_poap_data

    def _split_string_data(self, switch_data):
        # Helper function to parse <class 'ansible.utils.unsafe_proxy.AnsibleUnsafeText'>
        # string data into a proper python dictionary
        #
        try:
            parsed = json.loads(switch_data)
        except json.JSONDecodeError:
            # If the switch_data does not parse properly create a dict
            # with the keys and data value 'NOT_SET'
            parsed = {}
            parsed['gateway'] = "NOT_SET"
            parsed['modulesModel'] = "NOT_SET"

        return parsed

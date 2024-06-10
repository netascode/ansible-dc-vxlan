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

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        # self._supports_async = True
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False

        vpc_data = self._task.args['vpc_data']

        vpc_pairs = {}
        pair = 1
        # The following for loop creates a dictionary (vpc_pairs) that looks like this:
        #  {
        #    1: {'netascode-rtp-leaf1': False, 'netascode-rtp-leaf2': False},
        #    2: {'netascode-rtp-leaf3': False, 'netascode-rtp-leaf4': False}
        #  }
        for switch_pair in vpc_data['results']:
            vpc_pairs[pair] = {}
            for switch in switch_pair['response']:
                if not switch['isVpcConfigured']:
                    name = switch['hostName']
                    vpc_pairs[pair][name] = False
            pair += 1

        # vpc_data['results'][0]['response'][0]['isVpcConfigured']
        # vpc_data['results'][0]['response'][1]['isVpcConfigured']
        # vpc_data['results'][1]['response'][0]['isVpcConfigured']
        # vpc_data['results'][1]['response'][1]['isVpcConfigured']

        # if fabric_data.get('global').get('auth_proto') is None:
        #     results['failed'] = True
        #     results['msg'] = "Data model path 'vxlan.global.auth_proto' must be defined!"
        #     return results

        # if fabric_data.get('topology').get('switches') is not None:
        #     for switch in fabric_data['topology']['switches']:
        #         for key in ['management', 'role']:
        #             if switch.get(key) is None:
        #                 results['failed'] = True
        #                 results['msg'] = "Data model path 'vxlan.topology.switches.{0}.{1}' must be defined!".format(switch['name'], key)
        #                 return results

        return results
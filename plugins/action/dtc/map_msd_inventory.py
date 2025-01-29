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
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False

        parent_fabric_name = self._task.args['parent_fabric_name']
        model_data_overlay = self._task.args['model_data_overlay']

        msd_inventory = self._execute_module(
            module_name="cisco.dcnm.dcnm_inventory",
            module_args={
                "fabric": parent_fabric_name,
                "state": "query"
            },
            task_vars=task_vars,
            tmp=tmp
        )

        response = msd_inventory.get('response', [])
        msd_switches = {}

        if isinstance(response, str):
            if response == 'The queried switch is not part of the fabric configured':
                results['msd_switches'] = msd_switches
                return results

        for switch in response:
            msd_switches.update({switch['hostName']: switch['ipAddress']})
            msd_switches.update({switch['ipAddress']: switch['ipAddress']})
            msd_switches.update({switch['fabricName']: switch['fabricName']})

        # Cross reference msd_switches with the switches defined in
        # VRF and Network attach list.
        #
        # Only makes sense to check this if msd_switches actually has switches.
        if bool(msd_switches):
            results['msg'] = []
            for switch in model_data_overlay['vrf_attach_switches_list']:
                if switch not in msd_switches.keys():
                    results['failed'] = True
                    msg = f"Switch ({switch}) defined under vxlan.multisite.overlay.vrf_attach_groups"
                    msg += f" does not exist under this MSD fabric ({parent_fabric_name})"
                    results['msg'].append(msg)
            for switch in model_data_overlay['network_attach_switches_list']:
                if switch not in msd_switches.keys():
                    results['failed'] = True
                    msg = f"Switch ({switch}) defined under vxlan.multisite.overlay.network_attach_groups"
                    msg += f" does not exist under this MSD fabric ({parent_fabric_name})"
                    results['msg'].append(msg)

        results['msd_switches'] = msd_switches
        return results

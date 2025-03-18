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
        results['changed'] = False
        results['failed'] = False

        fabric = self._task.args["fabric"]
        msite_data = self._task.args["msite_data"]

        vrfs = msite_data['overlay_attach_groups']['vrfs']
        vrf_names = [vrf['name'] for vrf in vrfs]

        ndfc_vrfs = self._execute_module(
            module_name="cisco.dcnm.dcnm_vrf",
            module_args={
                "fabric": fabric,
                "state": "query"
            },
            task_vars=task_vars,
            tmp=tmp
        )

        if ndfc_vrfs.get('response'):
            ndfc_vrf_names = [ndfc_vrf['parent']['vrfName'] for ndfc_vrf in ndfc_vrfs['response']]

        if ndfc_vrfs.get('failed'):
            if ndfc_vrfs['failed']:
                results['failed'] = True
                results['msg'] = f"{ndfc_vrfs['msg']}"
                return results

        # Take the difference between the networks in the data model and the networks in NDFC
        # If the network is in NDFC but not in the data model, delete it
        diff_ndfc_vrf_names = [ndfc_vrf_name for ndfc_vrf_name in ndfc_vrf_names if ndfc_vrf_name not in vrf_names]

        if diff_ndfc_vrf_names:
            config = []
            for ndfc_vrf_name in diff_ndfc_vrf_names:
                config.append(
                    {
                        "vrf_name": ndfc_vrf_name,
                        "deploy": True
                    }
                )

            ndfc_deleted_vrfs = self._execute_module(
                module_name="cisco.dcnm.dcnm_vrf",
                module_args={
                    "fabric": fabric,
                    "config": config,
                    "state": "deleted"
                },
                task_vars=task_vars,
                tmp=tmp
            )

            if ndfc_deleted_vrfs.get('failed'):
                if ndfc_deleted_vrfs['failed']:
                    results['failed'] = True
                    results['msg'] = f"{ndfc_deleted_vrfs['msg']}"
                    return results

        return results

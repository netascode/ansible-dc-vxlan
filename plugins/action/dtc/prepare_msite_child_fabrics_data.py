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
from .rest_module_utils import get_rest_module

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False
        results['current_associated_child_fabrics'] = []
        results['to_be_removed'] = []
        results['to_be_added'] = []

        parent_fabric = self._task.args["parent_fabric"]
        child_fabrics = self._task.args["child_fabrics"]

        network_os = task_vars['ansible_network_os']
        rest_module = get_rest_module(network_os)
        if not rest_module:
            results['failed'] = True
            results['msg'] = f"Unsupported network_os: {network_os}"
            return results

        # This is actaully not an accurrate API endpoint as it returns all fabrics in NDFC, not just the fabrics associated with MSD
        # Therefore, we need to get the fabric associations response and filter out the fabrics that are not associated with the parent fabric (MSD)
        msd_fabric_associations = self._execute_module(
            module_name=rest_module,
            module_args={
                "method": "GET",
                "path": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/msd/fabric-associations",
            },
            task_vars=task_vars,
            tmp=tmp
        )

        # Build a list of child fabrics that are associated with the parent fabric (MSD)
        associated_child_fabrics = []
        for fabric in msd_fabric_associations.get('response').get('DATA'):
            if fabric.get('fabricParent') == parent_fabric:
                associated_child_fabrics.append(fabric.get('fabricName'))

        # Can probably remove this as I don't think it will be used
        results['current_associated_child_fabrics'] = associated_child_fabrics

        # Build a list of child fabrics that are to be removed from the parent fabric (MSD)
        child_fabrics_list = [child_fabric['name'] for child_fabric in child_fabrics]
        child_fabrics_to_be_removed = []
        child_fabric_to_be_removed = [fabric for fabric in associated_child_fabrics if fabric not in child_fabrics_list]
        child_fabrics_to_be_removed = child_fabrics_to_be_removed + child_fabric_to_be_removed

        results['to_be_removed'] = child_fabrics_to_be_removed

        # Build a list of desired child fabrics that are not added with the parent fabric (MSD)
        child_fabrics_to_be_added = []
        for fabric in child_fabrics:
            if fabric.get('name') not in associated_child_fabrics:
                child_fabrics_to_be_added.append(fabric.get('name'))

        results['to_be_added'] = child_fabrics_to_be_added

        return results

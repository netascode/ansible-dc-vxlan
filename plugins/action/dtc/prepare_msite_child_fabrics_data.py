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
    """
    Action plugin to build Multisite child fabrics add and remove list
    for management in Nexus Dashboard (ND) for MSD and MCFG parent fabrics.
    """
    def __init__(self, *args, **kwargs):
        super(ActionModule, self).__init__(*args, **kwargs)
        self.tmp = None
        self.task_vars = None

    def _get_child_fabrics_membership(self, path):
        """
        Get current child fabrics associated with the parent fabric
        in Nexus Dashboard for MSD and MCFG parent fabrics.
        """
        response = self._execute_module(
            module_name="cisco.dcnm.dcnm_rest",
            module_args={
                "method": "GET",
                "path": path,
            },
            task_vars=self.task_vars,
            tmp=self.tmp
        )

        return response

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False
        results['changed'] = False
        results['current_associated_child_fabrics'] = []
        results['to_be_removed'] = []
        results['to_be_added'] = []

        self.task_vars = task_vars
        self.tmp = tmp

        parent_fabric = self._task.args["parent_fabric"]
        parent_fabric_type = self._task.args["parent_fabric_type"]
        child_fabrics = self._task.args["child_fabrics"]

        if parent_fabric_type == 'MSD':
            # This is actaully not an accurrate API endpoint as it returns all fabrics in NDFC, not just the fabrics associated with MSD
            # Therefore, we need to get the fabric associations response and filter out the fabrics that are not associated with the parent fabric (MSD)
            path = "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/msd/fabric-associations"
            multisite_fabric_associations = self._get_child_fabrics_membership(path)

            # Build a list of child fabrics that are associated with the parent fabric (MSD)
            associated_child_fabrics = []
            for fabric in multisite_fabric_associations.get('response').get('DATA'):
                if fabric.get('fabricParent') == parent_fabric:
                    associated_child_fabrics.append(
                        {
                            'name': fabric.get('fabricName'),
                        }
                    )

        elif parent_fabric_type == 'MCFG':
            # Returns list of child fabrics associated with MCFG parent fabric with their respect fabric settings and attributes
            path = f"/onemanage/appcenter/cisco/ndfc/api/v1/onemanage/fabrics/{parent_fabric}"
            multisite_fabric_associations = self._get_child_fabrics_membership(path)

            # Build a list of child fabrics that are associated with the parent fabric (MCFG)
            associated_child_fabrics = []
            for fabric in multisite_fabric_associations.get('response').get('DATA').get('members'):
                associated_child_fabrics.append(
                    {
                        'name': fabric['fabricName'],
                        'cluster': fabric['clusterName'],
                    }
                )

        else:
            results['failed'] = True
            results['msg'] = f"Unsupported Multisite parent fabric type '{parent_fabric_type}' for fabric {parent_fabric}."
            return results

        # Can probably remove this as I don't think it will be used
        results['current_associated_child_fabrics'] = associated_child_fabrics

        # Build a list of child fabrics that are to be removed from the parent fabric (MSD/MCFG)
        # Get the set of desired child fabric names for efficient lookup
        child_fabric_names = [fabric['name'] for fabric in child_fabrics]

        child_fabrics_to_be_removed = [
            {'name': fabric['name'], 'cluster': fabric.get('cluster')}
            for fabric in associated_child_fabrics
            if fabric['name'] not in child_fabric_names
        ]

        results['to_be_removed'] = child_fabrics_to_be_removed

        associated_child_fabric_names = [fabric['name'] for fabric in associated_child_fabrics]

        # Build a list of desired child fabrics that are not added with the parent fabric (MSD/MCFG)
        child_fabrics_to_be_added = [
            {'name': fabric['name'], 'cluster': fabric.get('cluster')}
            for fabric in child_fabrics
            if fabric['name'] not in associated_child_fabric_names
        ]

        results['to_be_added'] = child_fabrics_to_be_added

        return results

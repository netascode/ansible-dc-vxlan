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
from ...plugin_utils.helper_functions import ndfc_get_fabric_attributes
from ...plugin_utils.helper_functions import ndfc_get_fabric_switches

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False
        results['md_msite'] = {}

        model_data = self._task.args["model_data"]
        parent_fabric = self._task.args["parent_fabric"]
        child_fabrics = self._task.args["child_fabrics"]

        # This is actaully not an accurrate API endpoint as it returns all fabrics in NDFC, not just the fabrics associated with MSD
        # Therefore, we need to get the fabric associations response and filter out the fabrics that are not associated with the parent fabric (MSD)
        msd_fabric_associations = self._execute_module(
            module_name="cisco.dcnm.dcnm_rest",
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

        results['child_fabrics_to_be_removed'] = child_fabrics_to_be_removed

        # Build a list of desired child fabrics that are not associated with the parent fabric (MSD)
        child_fabrics_to_be_associated = []
        for fabric in child_fabrics:
            if fabric.get('name') not in associated_child_fabrics:
                child_fabrics_to_be_associated.append(fabric.get('name'))

        results['child_fabrics_to_be_associated'] = child_fabrics_to_be_associated

        # Merge the lists of currently associated child fabrics and child fabrics to be associated
        # The assumption here is that the child fabric(s) that will be associated with the parent fabric (MSD)
        # in the create role will either be sucessful and we have the prepared data to work with or
        # the association will fail, resulting in runtime execution stopping, thus it doens't matter what prepared data we have.
        associated_child_fabrics = associated_child_fabrics + child_fabrics_to_be_associated

        # Can probably remove this as I don't think it will be used
        results['end_state_associated_child_fabrics'] = associated_child_fabrics

        child_fabrics_data = {}
        for fabric in associated_child_fabrics:
            child_fabrics_data.update({fabric: {}})
            child_fabrics_data[fabric].update({'attributes': ndfc_get_fabric_attributes(self, task_vars, tmp, fabric)})
            child_fabrics_data[fabric].update({'switches': ndfc_get_fabric_switches(self, task_vars, tmp, fabric)})

        results['child_fabrics_data'] = child_fabrics_data

        # Rebuild sm_data['vxlan']['multisite']['overlay']['vrf_attach_groups'] into
        # a structure that is easier to use just like MD_Extended.
        vrf_grp_name_list = []
        model_data['vxlan']['multisite']['overlay']['vrf_attach_groups_dict'] = {}
        model_data['vxlan']['multisite']['overlay']['vrf_attach_switches_list'] = []
        for grp in model_data['vxlan']['multisite']['overlay']['vrf_attach_groups']:
            model_data['vxlan']['multisite']['overlay']['vrf_attach_groups_dict'][grp['name']] = []
            vrf_grp_name_list.append(grp['name'])
            for switch in grp['switches']:
                model_data['vxlan']['multisite']['overlay']['vrf_attach_groups_dict'][grp['name']].append(switch)
            # If the switch is in the switch list and a hostname is used, replace the hostname with the management IP
            for switch in model_data['vxlan']['multisite']['overlay']['vrf_attach_groups_dict'][grp['name']]:
                for child_fabric in child_fabrics_data.keys():
                    for sw in child_fabrics_data[child_fabric]['switches']:
                        if switch['hostname'] == sw['hostname']:
                            switch['mgmt_ip_address'] = sw['mgmt_ip_address']

                # Append switch to a flat list of switches for cross comparison later when we query the
                # MSD fabric information.  We need to stop execution if the list returned by the MSD query
                # does not include one of these switches.
                model_data['vxlan']['multisite']['overlay']['vrf_attach_switches_list'].append(switch['hostname'])

        # Remove vrf_attach_group from vrf if the group_name is not defined
        for vrf in model_data['vxlan']['multisite']['overlay']['vrfs']:
            if 'vrf_attach_group' in vrf:
                if vrf.get('vrf_attach_group') not in vrf_grp_name_list:
                    del vrf['vrf_attach_group']

        # Rebuild sm_data['vxlan']['overlay']['network_attach_groups'] into
        # a structure that is easier to use.
        net_grp_name_list = []
        model_data['vxlan']['multisite']['overlay']['network_attach_groups_dict'] = {}
        model_data['vxlan']['multisite']['overlay']['network_attach_switches_list'] = []
        for grp in model_data['vxlan']['multisite']['overlay']['network_attach_groups']:
            model_data['vxlan']['multisite']['overlay']['network_attach_groups_dict'][grp['name']] = []
            net_grp_name_list.append(grp['name'])
            for switch in grp['switches']:
                model_data['vxlan']['multisite']['overlay']['network_attach_groups_dict'][grp['name']].append(switch)
            # If the switch is in the switch list and a hostname is used, replace the hostname with the management IP
            for switch in model_data['vxlan']['multisite']['overlay']['network_attach_groups_dict'][grp['name']]:
                for child_fabric in child_fabrics_data.keys():
                    for sw in child_fabrics_data[child_fabric]['switches']:
                        if switch['hostname'] == sw['hostname']:
                            switch['mgmt_ip_address'] = sw['mgmt_ip_address']
                # Append switch to a flat list of switches for cross comparison later when we query the
                # MSD fabric information.  We need to stop execution if the list returned by the MSD query
                # does not include one of these switches.
                model_data['vxlan']['multisite']['overlay']['network_attach_switches_list'].append(switch['hostname'])

        # Remove network_attach_group from net if the group_name is not defined
        for net in model_data['vxlan']['multisite']['overlay']['networks']:
            if 'network_attach_group' in net:
                if net.get('network_attach_group') not in net_grp_name_list:
                    del net['network_attach_group']

        results['overlay_attach_groups'] = model_data['vxlan']['multisite']['overlay']

        return results

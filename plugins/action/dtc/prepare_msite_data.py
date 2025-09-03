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
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import ndfc_get_fabric_attributes
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import ndfc_get_fabric_switches
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import ndfc_get_fabric_attributes_onepath
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import ndfc_get_fabric_switches_onepath
import re

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False
        results['child_fabrics_data'] = {}
        results['overlay_attach_groups'] = {}

        model_data = self._task.args["model_data"]
        parent_fabric = self._task.args["parent_fabric"]

        # This is actaully not an accurrate API endpoint as it returns all fabrics in NDFC, not just the fabrics associated with MSD
        # Therefore, we need to get the fabric associations response and filter out the fabrics that are not associated with the parent fabric (MSD)
        if model_data["vxlan"]["fabric"]["type"] == "MFD":
            mfd_fabric_associations = self._execute_module(
                module_name="cisco.dcnm.dcnm_rest",
                module_args={
                    "method": "GET",
                    "path": "/appcenter/cisco/ndfc/api/v1/onemanage/fabrics",
                },
                task_vars=task_vars,
                tmp=tmp
            )
            associated_child_fabrics = []
            for fabric in mfd_fabric_associations.get('response').get('DATA'):
                if fabric.get('fabricName') == parent_fabric:
                    for member in fabric["members"]:
                        associated_child_fabrics.append({
                            'fabric': member.get('fabricName'),
                            'cluster': member.get('clusterName'),
                            'type': member.get('fabricType')
                        })

            child_fabrics_data = {}
            for fabric in associated_child_fabrics:
                fabric_name = fabric['fabric']
                child_fabrics_data.update({fabric_name: {}})
                child_fabrics_data[fabric_name].update({'type': fabric['type']})
                child_fabrics_data[fabric_name].update({'attributes': ndfc_get_fabric_attributes_onepath(self, task_vars, tmp, fabric_name, fabric['cluster'])})
                child_fabrics_data[fabric_name].update({'switches': ndfc_get_fabric_switches_onepath(self, task_vars, tmp, fabric_name, fabric['cluster'])})
                child_fabrics_data[fabric_name].update({'cluster': fabric['cluster']})
            results['child_fabrics_data'] = child_fabrics_data
            
        else:
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

        # Get the fabric attributes and switches for each child fabric
        # These queries are potentially trying to get data for a fabric that is not associated with the parent fabric (MSD) yet
            child_fabrics_data = {}
            for fabric in associated_child_fabrics:
                child_fabrics_data.update({fabric: {}})
                child_fabrics_data[fabric].update(
                    {'type': [_fabric['fabricType'] for _fabric in msd_fabric_associations['response']['DATA'] if _fabric['fabricName'] == fabric][0]}
                )
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
                        # When switch is in preprovision, sw['hostname'] is None.
                        if sw.get('hostname') is not None:
                            # Compare switches with regex to catch hostname when ip domain-name is configured
                            regex_pattern = f"^{switch['hostname']}$|^{switch['hostname']}\\..*$"
                            if re.search(regex_pattern, sw['hostname']):
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
                        if sw.get('hostname') is not None:
                            regex_pattern = f"^{switch['hostname']}$|^{switch['hostname']}\\..*$"
                            if re.search(regex_pattern, sw['hostname']):
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

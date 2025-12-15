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
from ansible_collections.cisco.nac_dc_vxlan.plugins.filter.version_compare import version_compare
import re

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False
        results['child_fabrics_data'] = {}
        results['overlay_attach_groups'] = {}

        data_model = self._task.args["data_model"]
        parent_fabric = self._task.args["parent_fabric"]
        parent_fabric_type = self._task.args["parent_fabric_type"]

        nd_version = self._task.args["nd_version"]

        # Extract major, minor, patch and patch letter from nd_version
        # that is set in nac_dc_vxlan.dtc.connectivity_check role
        # Example nd_version: "3.1.1l" or "3.2.2m"
        # where 3.1.1/3.2.2 are major.minor.patch respectively
        # and l/m are the patch letter respectively
        nd_major_minor_patch = None
        nd_patch_letter = None
        match = re.match(r'^(\d+\.\d+\.\d+)([a-z])?$', nd_version)
        if match:
            nd_major_minor_patch = match.group(1)
            nd_patch_letter = match.group(2)

        if parent_fabric_type == 'MSD':
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

        elif parent_fabric_type == 'MCFG':
            # MCFG fabric associations API to get child fabrics associated with the parent MCFG fabric is performed differently than MSD
            # Need to query the parent MCFG fabric to get the associated child fabrics which also contains each child fabric's fabric setting attributes
            # Additionally, need to query each child fabric's switches separately using the child fabric's cluster name and proxy path based on ND version

            mcfg_fabric_associations = self._execute_module(
                module_name="cisco.dcnm.dcnm_rest",
                module_args={
                    "method": "GET",
                    "path": f"/onemanage/appcenter/cisco/ndfc/api/v1/onemanage/fabrics/{parent_fabric}",
                },
                task_vars=task_vars,
                tmp=tmp
            )

            # Build child fabrics data set that are associated with the parent fabric (MCFG)
            child_fabrics_data = {}
            for fabric in mcfg_fabric_associations.get('response').get('DATA').get('members'):
                # associated_child_fabrics.append(fabric.get('fabricName'))
                fabric_name = fabric.get('fabricName')
                fabric_cluster = fabric.get('clusterName')

                child_fabrics_data.update({fabric_name: {}})
                child_fabrics_data[fabric_name].update(
                    {'type': fabric.get('fabricType')}
                )
                child_fabrics_data[fabric_name].update(
                    {'attributes': fabric.get('nvPairs')}
                )

                proxy = ''
                if version_compare(nd_major_minor_patch, '3.2.2', '<='):
                    proxy = f'/onepath/{fabric_cluster}'
                elif version_compare(nd_major_minor_patch, '4.1.1', '>='):
                    proxy = f'/fedproxy/{fabric_cluster}'

                mcfg_child_fabric_switches = self._execute_module(
                    module_name="cisco.dcnm.dcnm_rest",
                    module_args={
                        "method": "GET",
                        "path": f"{proxy}/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/{fabric_name}/inventory/switchesByFabric",
                    },
                    task_vars=task_vars,
                    tmp=tmp
                )

                fabric_switches = []
                for fabric_switch in mcfg_child_fabric_switches['response']['DATA']:
                    if 'logicalName' in fabric_switch:
                        fabric_switches.append(
                            {
                                'hostname': fabric_switch['logicalName'],
                                'mgmt_ip_address': fabric_switch['ipAddress'],
                                'fabric_name': fabric_switch['fabricName'],
                                'serial_number': fabric_switch['serialNumber'],
                            }
                        )

                child_fabrics_data[fabric_name].update(
                    {'switches': fabric_switches}
                )

        else:
            results['failed'] = True
            results['msg'] = f"Unsupported parent_fabric_type '{parent_fabric_type}' provided. Supported types are 'MSD' and 'MCFG'."
            return results

        results['child_fabrics_data'] = child_fabrics_data

        all_child_fabric_switches = []
        for child_fabric in child_fabrics_data.keys():
            all_child_fabric_switches = all_child_fabric_switches + child_fabrics_data[child_fabric]['switches']

        results['switches'] = all_child_fabric_switches

        # Rebuild sm_data['vxlan']['multisite']['overlay']['vrf_attach_groups'] into
        # a structure that is easier to use just like data_model_extended.
        vrf_grp_name_list = []
        data_model['vxlan']['multisite']['overlay']['vrf_attach_groups_dict'] = {}
        data_model['vxlan']['multisite']['overlay']['vrf_attach_switches_list'] = []
        for grp in data_model['vxlan']['multisite']['overlay']['vrf_attach_groups']:
            data_model['vxlan']['multisite']['overlay']['vrf_attach_groups_dict'][grp['name']] = []
            vrf_grp_name_list.append(grp['name'])
            for switch in grp['switches']:
                data_model['vxlan']['multisite']['overlay']['vrf_attach_groups_dict'][grp['name']].append(switch)
            # If the switch is in the switch list and a hostname is used, replace the hostname with the management IP
            for switch in data_model['vxlan']['multisite']['overlay']['vrf_attach_groups_dict'][grp['name']]:
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
                data_model['vxlan']['multisite']['overlay']['vrf_attach_switches_list'].append(switch['hostname'])

        # Remove vrf_attach_group from vrf if the group_name is not defined
        for vrf in data_model['vxlan']['multisite']['overlay']['vrfs']:
            if 'vrf_attach_group' in vrf:
                if vrf.get('vrf_attach_group') not in vrf_grp_name_list:
                    del vrf['vrf_attach_group']

        # Rebuild sm_data['vxlan']['overlay']['network_attach_groups'] into
        # a structure that is easier to use.
        net_grp_name_list = []
        data_model['vxlan']['multisite']['overlay']['network_attach_groups_dict'] = {}
        data_model['vxlan']['multisite']['overlay']['network_attach_switches_list'] = []
        for grp in data_model['vxlan']['multisite']['overlay']['network_attach_groups']:
            data_model['vxlan']['multisite']['overlay']['network_attach_groups_dict'][grp['name']] = []
            net_grp_name_list.append(grp['name'])
            for switch in grp['switches']:
                data_model['vxlan']['multisite']['overlay']['network_attach_groups_dict'][grp['name']].append(switch)
            # If the switch is in the switch list and a hostname is used, replace the hostname with the management IP
            for switch in data_model['vxlan']['multisite']['overlay']['network_attach_groups_dict'][grp['name']]:
                for child_fabric in child_fabrics_data.keys():
                    for sw in child_fabrics_data[child_fabric]['switches']:
                        if sw.get('hostname') is not None:
                            regex_pattern = f"^{switch['hostname']}$|^{switch['hostname']}\\..*$"
                            if re.search(regex_pattern, sw['hostname']):
                                switch['mgmt_ip_address'] = sw['mgmt_ip_address']
                # Append switch to a flat list of switches for cross comparison later when we query the
                # MSD fabric information.  We need to stop execution if the list returned by the MSD query
                # does not include one of these switches.
                data_model['vxlan']['multisite']['overlay']['network_attach_switches_list'].append(switch['hostname'])

        # Remove network_attach_group from net if the group_name is not defined
        for net in data_model['vxlan']['multisite']['overlay']['networks']:
            if 'network_attach_group' in net:
                if net.get('network_attach_group') not in net_grp_name_list:
                    del net['network_attach_group']

        results['overlay_attach_groups'] = data_model['vxlan']['multisite']['overlay']

        return results

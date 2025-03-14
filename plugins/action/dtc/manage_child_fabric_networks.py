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
from ansible.template import Templar
from ansible.errors import AnsibleFileNotFound


import json

display = Display()

# Path to Jinja template files relative to create role
MSD_CHILD_FABRIC_NETWORK_TEMPLATE = "/../common/templates/ndfc_networks/msd_fabric/child_fabric/msd_child_fabric_network.j2"


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['changed'] = False
        results['failed'] = False
        results['child_fabrics_changed'] = []

        msite_data = self._task.args["msite_data"]
        state = self._task.args["state"]

        networks = msite_data['overlay_attach_groups']['networks']

        if state == 'present':
            network_attach_groups_dict = msite_data['overlay_attach_groups']['network_attach_groups']

            child_fabrics = msite_data['child_fabrics_data']

            for network in networks:
                network_attach_group_switches = [
                    network_attach_groups_dict['switches']
                    for network_attach_groups_dict in network_attach_groups_dict
                    if network_attach_groups_dict['name'] == network['network_attach_group']
                ][0]
                network_attach_group_switches_mgmt_ip_addresses = [
                    network_attach_group_switch['mgmt_ip_address']
                    for network_attach_group_switch in network_attach_group_switches
                ]

                for child_fabric in child_fabrics.keys():
                    child_fabric_attributes = child_fabrics[child_fabric]['attributes']
                    child_fabric_switches = child_fabrics[child_fabric]['switches']
                    child_fabric_switches_mgmt_ip_addresses = [child_fabric_switch['mgmt_ip_address'] for child_fabric_switch in child_fabric_switches]

                    is_intersection = set(network_attach_group_switches_mgmt_ip_addresses).intersection(set(child_fabric_switches_mgmt_ip_addresses))

                    if is_intersection:
                        # Need to clean these up and make them more dynamic
                        if network.get('netflow_enable'):
                            if child_fabric_attributes['ENABLE_NETFLOW'] == 'false':
                                error_msg = (
                                    f"For fabric {child_fabric}; NetFlow is not enabled in the fabric settings. "
                                    "To enable NetFlow in Network, you need to first enable it in the fabric settings."
                                )
                                display.error(error_msg)
                                results['failed'] = True
                                results['msg'] = error_msg
                                return results

                        if network.get('trm_enable'):
                            if child_fabric_attributes['ENABLE_TRM'] == 'false':
                                error_msg = (
                                    f"For fabric {child_fabric}; TRM is not enabled in the fabric settings. "
                                    "To enable TRM in Network, you need to first enable it in the fabric settings."
                                )
                                display.error(error_msg)
                                results['failed'] = True
                                results['msg'] = error_msg
                                return results

                        # Need to check data model and support for enabling TRMv6 in the fabric settings
                        # if network.get('trm_enable'):
                        #     if child_fabric_attributes['ENABLE_TRMv6'] == 'false':
                        #         error_msg = (
                        #             f"For fabric {child_fabric}; TRMv6 is not enabled in the fabric settings. "
                        #             "To enable TRMv6 in Network, you need to first enable it in the fabric settings."
                        #         )
                        #         display.error(error_msg)
                        #         results['failed'] = True
                        #         results['msg'] = error_msg
                        #         return results

                        ndfc_net = self._execute_module(
                            module_name="cisco.dcnm.dcnm_rest",
                            module_args={
                                "method": "GET",
                                "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/{child_fabric}/networks/{network['name']}",
                            },
                            task_vars=task_vars,
                            tmp=tmp
                        )

                        ndfc_net_response_data = ndfc_net['response']['DATA']
                        ndfc_net_template_config = json.loads(ndfc_net_response_data['networkTemplateConfig'])

                        # Check for differences between the data model and the template config from NDFC for the
                        # attributes that are configurable by the user in a child fabric.
                        # Note: This excludes IPv6 related attributes at this time as they are not yet supported fully in the data model.
                        if (
                            (ndfc_net_template_config['loopbackId'] != network.get('dhcp_loopback_id', "")) or
                            (ndfc_net_template_config['ENABLE_NETFLOW'] != str(network.get('netflow_enable', False)).lower()) or
                            (ndfc_net_template_config['VLAN_NETFLOW_MONITOR'] != network.get('vlan_netflow_monitor', "")) or
                            (ndfc_net_template_config['trmEnabled'] != str(network.get('trm_enable', False)).lower()) or
                            (ndfc_net_template_config['mcastGroup'] != network.get('multicast_group_address'))
                        ):
                            results['child_fabrics_changed'].append(child_fabric)

                            # Combine task_vars with local_vars for template rendering
                            net_vars = {}
                            net_vars.update({'fabric_name': ndfc_net_response_data['fabric']})
                            net_vars.update({'network_name': ndfc_net_response_data['networkName']})
                            net_vars.update(
                                {
                                    'ndfc': ndfc_net_template_config,
                                    'dm': network
                                },
                            )

                            role_path = task_vars.get('role_path')
                            template_path = role_path + MSD_CHILD_FABRIC_NETWORK_TEMPLATE

                            # Attempt to find and read the template file
                            try:
                                template_full_path = self._find_needle('templates', template_path)
                                with open(template_full_path, 'r') as template_file:
                                    template_content = template_file.read()
                            except (IOError, AnsibleFileNotFound) as e:
                                return {'failed': True, 'msg': f"Template file not found or unreadable: {str(e)}"}

                            # Create a Templar instance
                            templar = Templar(loader=self._loader, variables=net_vars)

                            # Render the template with the combined variables
                            rendered_content = templar.template(template_content)
                            rendered_to_nice_json = templar.environment.filters['to_nice_json'](rendered_content)

                            ndfc_net_update = self._execute_module(
                                module_name="cisco.dcnm.dcnm_rest",
                                module_args={
                                    "method": "PUT",
                                    "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/{child_fabric}/networks/{network['name']}",
                                    "data": rendered_to_nice_json
                                },
                                task_vars=task_vars,
                                tmp=tmp
                            )

                            # Successful response:
                            # {
                            #     "changed": false,
                            #     "response": {
                            #         "RETURN_CODE": 200,
                            #         "METHOD": "PUT",
                            #         "REQUEST_PATH": "https://10.15.0.110:443/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/nac-fabric1/networks/NaC-Net01", # noqa: E501
                            #         "MESSAGE": "OK",
                            #         "DATA": {
                            #         }
                            #     },
                            #     "invocation": {
                            #         "module_args": {
                            #         "method": "PUT",
                            #         "path": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/nac-fabric1/networks/NaC-Net01", # noqa: E501
                            #         "data": "{\n    \"displayName\": \"NaC-Net01\",\n    \"fabric\": \"nac-fabric1\",\n    \"hierarchicalKey\": \"nac-fabric1\",\n    \"networkExtensionTemplate\": \"Default_Network_Extension_Universal\",\n    \"networkId\": \"130001\",\n    \"networkName\": \"NaC-Net01\",\n    \"networkTemplate\": \"Default_Network_Universal\",\n    \"networkTemplateConfig\": \" {\\'vrfName\\': \\'NaC-VRF01\\', \\'networkName\\': \\'NaC-Net01\\', \\'vlanId\\': \\'2301\\', \\'vlanName\\': \\'NaC-Net01_vlan2301\\', \\'segmentId\\': \\'130001\\', \\'intfDescription\\': \\'Configured by Ansible NetAsCode\\', \\'gatewayIpAddress\\': \\'192.168.1.1/24\\', \\'gatewayIpV6Address\\': \\'\\', \\'mtu\\': \\'9216\\', \\'isLayer2Only\\': \\'false\\', \\'suppressArp\\': \\'false\\', \\'mcastGroup\\': \\'239.1.1.1\\', \\'tag\\': \\'12345\\', \\'secondaryGW1\\': \\'\\', \\'secondaryGW2\\': \\'\\', \\'secondaryGW3\\': \\'\\', \\'secondaryGW4\\': \\'\\', \\'loopbackId\\': \\'\\', \\'dhcpServerAddr1\\': \\'\\', \\'vrfDhcp\\': \\'\\', \\'dhcpServerAddr2\\': \\'\\', \\'vrfDhcp2\\': \\'\\', \\'dhcpServerAddr3\\': \\'\\', \\'vrfDhcp3\\': \\'\\', \\'ENABLE_NETFLOW\\': \\'false\\', \\'SVI_NETFLOW_MONITOR\\': \\'\\', \\'VLAN_NETFLOW_MONITOR\\': \\'\\', \\'enableIR\\': \\'false\\', \\'trmEnabled\\': True, \\'igmpVersion\\': \\'2\\', \\'trmV6Enabled\\': \\'\\', \\'rtBothAuto\\': \\'false\\', \\'enableL3OnBorder\\': \\'false\\', \\'enableL3OnBorderVpcBgw\\': \\'false\\', \\'nveId\\': \\'1\\', \\'type\\': \\'Normal\\'}\",\n    \"type\": \"Normal\",\n    \"vrf\": \"NaC-VRF01\"\n}" # noqa: E501
                            #         }
                            #     },
                            #     "_ansible_parsed": true
                            # }
                            if ndfc_net_update.get('response'):
                                if ndfc_net_update['response']['RETURN_CODE'] == 200:
                                    results['changed'] = True

                            # Failed response:
                            # {
                            #     "failed": true,
                            #     "msg": {
                            #         "RETURN_CODE": 500,
                            #         "METHOD": "PUT",
                            #         "REQUEST_PATH": "https://10.15.0.110:443/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/nac-fabric1/networks/NaC-Net01", # noqa: E501
                            #         "MESSAGE": "Internal Server Error",
                            #         "DATA": {
                            #             "path": "/rest/top-down/fabrics/nac-fabric1/networks/NaC-Net01",
                            #             "Error": "Internal Server Error",
                            #             "message": "Netflow not enabled in Fabric Settings",
                            #             "timestamp": "2025-02-25 21:54:26.633",
                            #             "status": "500"
                            #         }
                            #     },
                            #     "invocation": {
                            #         "module_args": {
                            #             "method": "PUT",
                            #             "path": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/nac-fabric1/networks/NaC-Net01", # noqa: E501
                            #             "data": "{\n    \"displayName\": \"NaC-Net01\",\n    \"fabric\": \"nac-fabric1\",\n    \"hierarchicalKey\": \"nac-fabric1\",\n    \"networkExtensionTemplate\": \"Default_Network_Extension_Universal\",\n    \"networkId\": \"130001\",\n    \"networkName\": \"NaC-Net01\",\n    \"networkTemplate\": \"Default_Network_Universal\",\n    \"networkTemplateConfig\": \" {\\'vrfName\\': \\'NaC-VRF01\\', \\'networkName\\': \\'NaC-Net01\\', \\'vlanId\\': \\'2301\\', \\'vlanName\\': \\'NaC-Net01_vlan2301\\', \\'segmentId\\': \\'130001\\', \\'intfDescription\\': \\'Configured by Ansible NetAsCode\\', \\'gatewayIpAddress\\': \\'192.168.1.1/24\\', \\'gatewayIpV6Address\\': \\'\\', \\'mtu\\': \\'9216\\', \\'isLayer2Only\\': \\'false\\', \\'suppressArp\\': \\'false\\', \\'mcastGroup\\': \\'239.1.1.1\\', \\'tag\\': \\'12345\\', \\'secondaryGW1\\': \\'\\', \\'secondaryGW2\\': \\'\\', \\'secondaryGW3\\': \\'\\', \\'secondaryGW4\\': \\'\\', \\'loopbackId\\': \\'\\', \\'dhcpServerAddr1\\': \\'\\', \\'vrfDhcp\\': \\'\\', \\'dhcpServerAddr2\\': \\'\\', \\'vrfDhcp2\\': \\'\\', \\'dhcpServerAddr3\\': \\'\\', \\'vrfDhcp3\\': \\'\\', \\'ENABLE_NETFLOW\\': True, \\'SVI_NETFLOW_MONITOR\\': \\'\\', \\'VLAN_NETFLOW_MONITOR\\': \\'blah\\', \\'enableIR\\': \\'false\\', \\'trmEnabled\\': True, \\'igmpVersion\\': \\'2\\', \\'trmV6Enabled\\': \\'\\', \\'rtBothAuto\\': \\'false\\', \\'enableL3OnBorder\\': \\'false\\', \\'enableL3OnBorderVpcBgw\\': \\'false\\', \\'nveId\\': \\'1\\', \\'type\\': \\'Normal\\'}\",\n    \"type\": \"Normal\",\n    \"vrf\": \"NaC-VRF01\"\n}" # noqa: E501
                            #         }
                            #     },
                            #     "_ansible_parsed": true
                            # }
                            if ndfc_net_update.get('msg'):
                                if ndfc_net_update['msg']['RETURN_CODE'] != 200:
                                    results['failed'] = True
                                    results['msg'] = f"For fabric {child_fabric}; {ndfc_net_update['msg']['DATA']['message']}"
                                    return results

        if state == 'absent':
            fabric = self._task.args["fabric"]
            network_names = [network['name'] for network in networks]

            ndfc_networks = self._execute_module(
                module_name="cisco.dcnm.dcnm_network",
                module_args={
                    "fabric": fabric,
                    "state": "query"
                },
                task_vars=task_vars,
                tmp=tmp
            )

            # Successful query:
            # {
            #     "changed": false,
            #     "diff": [],
            #     "response": [{
            #         "parent":{
            #             "id":442,
            #             "fabric": "nac-msd1",
            #             "networkName": "NaC-Net01",
            #             "displayName": "NaC-Net01",
            #             "networkId": 130001,
            #             "networkTemplate": "Default_Network_Universal",
            #             "networkExtensionTemplate": "Default_Network_Extension_Universal",
            #             "networkTemplateConfig": {
            #                 "suppressArp": "false",
            #                 "secondaryGW3": "",
            #                 "secondaryGW2": "",
            #                 "secondaryGW1": "",
            #                 "vlanId": "2301",
            #                 "gatewayIpAddress": "192.168.1.1/24",
            #                 "vlanName": "NaC-Net01_vlan2301",
            #                 "type": "Normal",
            #                 "mtu": "9216",
            #                 "rtBothAuto": "false",
            #                 "isLayer2Only": "false",
            #                 "intfDescription": "Configured by Ansible NetAsCode",
            #                 "segmentId": "130001",
            #                 "gatewayIpV6Address": "",
            #                 "tag": "12345",
            #                 "nveId": "1",
            #                 "secondaryGW4": "",
            #                 "vrfName": "NaC-VRF01"
            #             },
            #             "vrf": "NaC-VRF01",
            #             "tenantName": "None",
            #             "serviceNetworkTemplate": "None",
            #             "source": "None",
            #             "interfaceGroups": "",
            #             "primaryNetworkId": -1,
            #             "type": "Normal",
            #             "primaryNetworkName": "None",
            #             "vlanId": "None",
            #             "vlanName": "None",
            #             "networkStatus": "DEPLOYED",
            #             "hierarchicalKey": "nac-msd1"
            #         },
            #         "attach": [
            #             {
            #                 "networkName": "NaC-Net01",
            #                 "displayName": "NaC-Net01",
            #                 "switchName": "nac-s1-leaf1",
            #                 "switchRole": "leaf",
            #                 "fabricName": "nac-fabric1",
            #                 "lanAttachState": "DEPLOYED",
            #                 "isLanAttached": true,
            #                 "portNames": "Ethernet1/13,Ethernet1/14",
            #                 "switchSerialNo": "952DTHDC6DE",
            #                 "peerSerialNo": "None",
            #                 "switchDbId": 1680730,
            #                 "ipAddress": "10.15.33.13",
            #                 "networkId": 130001,
            #                 "vlanId": 2301,
            #                 "instanceValues": "{\"isVPC\":\"false\"}",
            #                 "entityName": "NaC-Net01",
            #                 "interfaceGroups": "None"
            #             }
            #         ]
            #     }],
            #     "invocation": {
            #         "module_args": {
            #             "fabric": "nac-msd1",
            #             "state": "query",
            #             "config": "None"
            #         }
            #     },
            #     "_ansible_parsed": true
            # }
            if ndfc_networks.get('response'):
                ndfc_network_names = [ndfc_network['parent']['networkName'] for ndfc_network in ndfc_networks['response']]

            # Failed query:
            # {
            #     "failed": true,
            #     "msg": "Fabric fabric missing on DCNM or does not have any switches",
            #     "invocation": {
            #         "module_args": {
            #             "fabric":"fabric",
            #             "state":"query",
            #             "config":"None"
            #         }
            #     },
            #     "_ansible_parsed": true
            # }
            if ndfc_networks.get('failed'):
                if ndfc_networks['failed']:
                    results['failed'] = True
                    results['msg'] = f"{ndfc_networks['msg']}"
                    return results

            # Take the difference between the networks in the data model and the networks in NDFC
            # If the network is in NDFC but not in the data model, delete it
            diff_ndfc_network_names = [ndfc_network_name for ndfc_network_name in ndfc_network_names if ndfc_network_name not in network_names]

            if diff_ndfc_network_names:
                config = []
                for ndfc_network_name in diff_ndfc_network_names:
                    config.append(
                        {
                            "net_name": ndfc_network_name,
                            "deploy": True
                        }
                    )

                ndfc_deleted_networks = self._execute_module(
                    module_name="cisco.dcnm.dcnm_network",
                    module_args={
                        "fabric": fabric,
                        "config": config,
                        "state": "deleted"
                    },
                    task_vars=task_vars,
                    tmp=tmp
                )

                if ndfc_deleted_networks.get('failed'):
                    if ndfc_deleted_networks['failed']:
                        results['failed'] = True
                        results['msg'] = f"{ndfc_deleted_networks['msg']}"
                        return results

        return results

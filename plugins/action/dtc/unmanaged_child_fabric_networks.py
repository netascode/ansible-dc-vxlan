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

        networks = msite_data['overlay_attach_groups']['networks']
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
            else:
                results['changed'] = True

        return results

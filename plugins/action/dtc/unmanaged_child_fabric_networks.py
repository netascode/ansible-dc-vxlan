# Copyright (c) 2025 Cisco Systems, Inc. and its affiliates
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
    Action plugin to determine what Networks are to be removed from Nexus Dashboard (ND)
    through comparison with the desired state in data model to ND state or through
    the diff run framework option.
    """
    def __init__(self, *args, **kwargs):
        super(ActionModule, self).__init__(*args, **kwargs)
        self.tmp = None
        self.task_vars = None
        self.nd_networks = {}
        self.results = {}

    def get_nd_networks(self, fabric):
        self.nd_networks = self._execute_module(
            module_name="cisco.dcnm.dcnm_network",
            module_args={
                "fabric": fabric,
                "state": "query"
            },
            task_vars=self.task_vars,
            tmp=self.tmp
        )

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
        if self.nd_networks.get('failed'):
            if self.nd_networks['failed']:
                self.results['failed'] = True
                self.results['msg'] = f"{self.nd_networks['msg']}"
                return self.results

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

    def dm_nd_diff(self, fabric, data):
        networks = data['overlay_attach_groups']['networks']
        network_names = [network['name'] for network in networks]

        diff_ndfc_network_names = []
        config = []

        if self.nd_networks.get('response'):
            ndfc_network_names = [ndfc_network['parent']['networkName'] for ndfc_network in self.nd_networks['response']]

            # Take the difference between the networks in the data model and the networks in NDFC
            # If the network is in NDFC but not in the data model, delete it
            diff_ndfc_network_names = [ndfc_network_name for ndfc_network_name in ndfc_network_names if ndfc_network_name not in network_names]

        display.warning(f"Removing network_names: {diff_ndfc_network_names} from fabric: {fabric}")
        if diff_ndfc_network_names:
            for ndfc_network_name in diff_ndfc_network_names:
                config.append(
                    {
                        "net_name": ndfc_network_name,
                        "deploy": True
                    }
                )

        return config

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['changed'] = False
        results['failed'] = False

        self.tmp = tmp
        self.task_vars = task_vars

        fabric = self._task.args["fabric"]
        # data to use for deleting unmanaged VRFs based on either
        # (a) diff run data or (b) data model state compared to ND state
        data = self._task.args["data"]
        diff_run = self._task.args.get("diff_run", False)

        if not diff_run:
            self.get_nd_networks(fabric)
            if self.results.get('failed'):
                results['failed'] = self.results['failed']
                results['msg'] = self.results['msg']

            config = self.dm_nd_diff(fabric, data)
        else:
            config = data

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

        # See above for failed query example
        if ndfc_deleted_networks.get('failed'):
            if ndfc_deleted_networks['failed']:
                results['failed'] = True
                results['msg'] = f"{ndfc_deleted_networks['msg']}"
                return results
        else:
            results['changed'] = True

        return results

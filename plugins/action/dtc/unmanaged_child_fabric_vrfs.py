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
        if ndfc_vrfs.get('failed'):
            if ndfc_vrfs['failed']:
                results['failed'] = True
                results['msg'] = f"{ndfc_vrfs['msg']}"
                return results

        # Successful query:
        # {
        #   "changed": false,
        #   "diff":[],
        #   "response": [
        #       {
        #         "parent": {
        #             "fabric": "nac-msd1",
        #             "vrfName": "NaC-VRF01",
        #             "enforce": "None",
        #             "defaultSGTag": "None",
        #             "vrfTemplate": "Default_VRF_Universal",
        #             "vrfExtensionTemplate": "Default_VRF_Extension_Universal",
        #             "vrfTemplateConfig": "{\"routeTargetExportEvpn\":\"\",\"routeTargetImport\":\"\",\"vrfVlanId\":\"2001\",\"vrfDescription\":\"Configured by Ansible NetAsCode\",\"disableRtAuto\":\"false\",\"vrfSegmentId\":\"150001\",\"maxBgpPaths\":\"1\",\"maxIbgpPaths\":\"2\",\"routeTargetExport\":\"\",\"ipv6LinkLocalFlag\":\"true\",\"mtu\":\"9216\",\"vrfRouteMap\":\"FABRIC-RMAP-REDIST-SUBNET\",\"vrfVlanName\":\"\",\"tag\":\"12345\",\"nveId\":\"1\",\"vrfIntfDescription\":\"Configured by Ansible NetAsCode\",\"vrfName\":\"NaC-VRF01\",\"routeTargetImportEvpn\":\"\"}", # noqa: E501
        #             "tenantName": "None",
        #             "id": 813,
        #             "vrfId": 150001,
        #             "serviceVrfTemplate": "None",
        #             "source": "None",
        #             "vrfStatus": "DEPLOYED",
        #             "hierarchicalKey": "nac-msd1"
        #       },
        #       "attach":[
        #         {
        #           "vrfName": "NaC-VRF01",
        #           "templateName": "Default_VRF_Universal",
        #           "switchDetailsList": [{
        #                 "switchName": "nac-s1-leaf1",
        #                 "vlan": 2001,
        #                 "serialNumber": "952DTHDC6DE",
        #                 "peerSerialNumber": "9BQPNWEB31K",
        #                 "extensionValues": "",
        #                 "extensionPrototypeValues": [],
        #                 "islanAttached": true,
        #                 "lanAttachedState": "DEPLOYED",
        #                 "errorMessage": "None",
        #                 "instanceValues": "{\"loopbackIpV6Address\":\"\",\"loopbackId\":\"\",\"deviceSupportL3VniNoVlan\":\"false\",\"switchRouteTargetImportEvpn\":\"\",\"loopbackIpAddress\":\"\",\"switchRouteTargetExportEvpn\":\"\"}", # noqa: E501
        #                 "freeformConfig": "",
        #                 "role": "leaf",
        #                 "vlanModifiable": true,
        #                 "showVlan": true
        #             },
        #             {
        #               "switchName": "nac-s1-leaf2",
        #               "vlan": 2001,
        #               "serialNumber": "9BQPNWEB31K",
        #               "peerSerialNumber": "952DTHDC6DE",
        #               "extensionValues": "",
        #               "extensionPrototypeValues": [],
        #               "islanAttached": true,
        #               "lanAttachedState": "DEPLOYED",
        #               "errorMessage": "None",
        #               "instanceValues": "{\"loopbackIpV6Address\":\"\",\"loopbackId\":\"\",\"deviceSupportL3VniNoVlan\":\"false\",\"switchRouteTargetImportEvpn\":\"\",\"loopbackIpAddress\":\"\",\"switchRouteTargetExportEvpn\":\"\"}", # noqa: E501
        #               "freeformConfig": "",
        #               "role": "leaf",
        #               "vlanModifiable": true,
        #               "showVlan": true
        #             }
        #           ]
        #         }
        #       ]
        #     }
        #   ],
        #   "invocation": {
        #     "module_args":
        #     {
        #       "fabric": "nac-msd1",
        #       "state": "query",
        #       "config": "None"
        #     }
        #   },
        #   "_ansible_parsed": true
        # }
        diff_ndfc_vrf_names = []
        if ndfc_vrfs.get('response'):
            ndfc_vrf_names = [ndfc_vrf['parent']['vrfName'] for ndfc_vrf in ndfc_vrfs['response']]

            # Take the difference between the vrfs in the data model and the vrfs in NDFC
            # If the vrf is in NDFC but not in the data model, delete it
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

            # See above for failed query example
            if ndfc_deleted_vrfs.get('failed'):
                if ndfc_deleted_vrfs['failed']:
                    results['failed'] = True
                    results['msg'] = f"{ndfc_deleted_vrfs['msg']}"
                    return results
            else:
                results['changed'] = True

        return results

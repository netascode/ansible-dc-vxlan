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
        results['child_fabrics_moved'] = False

        parent_fabric = self._task.args['parent_fabric']
        child_fabrics = self._task.args['child_fabrics']
        state = self._task.args['state']

        if state == 'present':
            for fabric in child_fabrics:
                json_data = '{"destFabric":"%s","sourceFabric":"%s"}' % (parent_fabric, fabric)
                add_fabric_result = self._execute_module(
                    module_name=task_vars['ansible_network_os_rest'],
                    module_args={
                        "method": "POST",
                        "path": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/msdAdd",
                        "json_data": json_data
                    },
                    task_vars=task_vars,
                    tmp=tmp
                )

                if add_fabric_result.get('failed'):
                    results['failed'] = True
                    results['msg'] = f"{add_fabric_result['msg']['MESSAGE']}: {add_fabric_result['msg']['DATA']}"
                    break

                # If a child fabric is successfully added under an MSD fabric set a flag
                # indicating this so that it can be used later to prevent managing VRFs
                # and Networks.  If we dont prevent this then the VRFs and Networks could
                # be removed as part of moving the child fabric.
                #
                # TBD: This flag is not actually being used currently.  Discuss with team.
                results['child_fabrics_moved'] = True

                results['changed'] = True

        if state == 'absent':
            for fabric in child_fabrics:
                json_data = '{"destFabric":"%s","sourceFabric":"%s"}' % (parent_fabric, fabric)
                remove_fabric_result = self._execute_module(
                    module_name=task_vars['ansible_network_os_rest'],
                    module_args={
                        "method": "POST",
                        "path": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/msdExit",
                        "json_data": json_data
                    },
                    task_vars=task_vars,
                    tmp=tmp
                )

                if remove_fabric_result.get('failed'):
                    results['failed'] = True
                    results['msg'] = f"{remove_fabric_result['msg']['MESSAGE']}: {remove_fabric_result['msg']['DATA']}"
                    break

                results['changed'] = True

        return results


#   cisco.dcnm.dcnm_rest:
#     method: POST
#     path: /appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/msdAdd
#     json_data: '{"destFabric":"nac-msd","sourceFabric":"nac-ndfc1"}'

# https://rtp-ndfc1.cisco.com/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/msd/fabric-associations/
# GET
# Response:
# "response": {
#     "DATA": [
#         {
#             "fabricId": 2,
#             "fabricName": "nac-fabric1",
#             "fabricParent": "None",
#             "fabricState": "standalone",
#             "fabricTechnology": "VXLANFabric",
#             "fabricType": "Switch_Fabric"
#         },
#         {
#             "fabricId": 3,
#             "fabricName": "nac-fabric2",
#             "fabricParent": "nac-msd1",
#             "fabricState": "member",
#             "fabricTechnology": "VXLANFabric",
#             "fabricType": "Switch_Fabric"
#         },
#         {
#             "fabricId": 4,
#             "fabricName": "nac-isn1",
#             "fabricParent": "None",
#             "fabricState": "standalone",
#             "fabricTechnology": "External",
#             "fabricType": "External"
#         },
#         {
#             "fabricId": 5,
#             "fabricName": "nac-msd1",
#             "fabricParent": "None",
#             "fabricState": "msd",
#             "fabricTechnology": "VXLANFabric",
#             "fabricType": "MSD"
#         }
#     ],
#     "MESSAGE": "OK",
#     "METHOD": "GET",
#     "REQUEST_PATH": "https://10.15.0.110:443/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/msd/fabric-associations",
#     "RETURN_CODE": 200
#     }

# https://rtp-ndfc1.cisco.com/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/msdAdd
# POST
# {"destFabric":"nac-msd","sourceFabric":"nac-ndfc1"}

# https://rtp-ndfc1.cisco.com/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/msdExit
# POST
# {"destFabric":"nac-msd","sourceFabric":"nac-ndfc1"}

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
        results['failed'] = False

        fabric_associations = self._task.args['fabric_associations'].get('response').get('DATA')
        parent_fabric_name = self._task.args['parent_fabric_name']
        child_fabrics = self._task.args['child_fabrics']
        operation = self._task.args['operation']

        # Build a list of child fabrics that are associated with the parent fabric
        associated_child_fabrics = []
        for fabric in fabric_associations:
            if fabric.get('fabricParent') == parent_fabric_name:
                associated_child_fabrics.append(fabric.get('fabricName'))

        if operation == 'add':
            for fabric in child_fabrics:
                if fabric.get('name') not in associated_child_fabrics:
                    json_data = '{"destFabric":"%s","sourceFabric":"%s"}' % (parent_fabric_name, fabric.get('name'))
                    add_fabric_result = self._execute_module(
                        module_name="cisco.dcnm.dcnm_rest",
                        module_args={
                            "method": "POST",
                            "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/msdAdd",
                            "json_data": json_data
                        },
                        task_vars=task_vars,
                        tmp=tmp
                    )

                    if add_fabric_result.get('failed'):
                        results['failed'] = True
                        results['msg'] = f"{add_fabric_result['msg']['MESSAGE']}: {add_fabric_result['msg']['DATA']}"
                        break

                    results['changed'] = True
        
        if operation == 'remove':
            for associated_child_fabric in associated_child_fabrics:
                if not any(associated_child_fabric == child_fabric['name'] for child_fabric in child_fabrics):
                    json_data = '{"destFabric":"%s","sourceFabric":"%s"}' % (parent_fabric_name, associated_child_fabric)
                    remove_fabric_result = self._execute_module(
                        module_name="cisco.dcnm.dcnm_rest",
                        module_args={
                            "method": "POST",
                            "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/msdExit",
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



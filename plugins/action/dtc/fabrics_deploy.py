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

        fabrics = self._task.args["fabrics"]

        for fabric in fabrics:
            display.display(f"Executing config-deploy on Fabric: {fabric}")
            ndfc_deploy = self._execute_module(
                module_name="cisco.nd.nd_rest",
                module_args={
                    "method": "POST",
                    "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/{fabric}/config-deploy?forceShowRun=false",
                },
                task_vars=task_vars,
                tmp=tmp
            )

            # Successful response:
            # {
            #     "changed": false,
            #     "response": {
            #         "RETURN_CODE": 200,
            #         "METHOD": "POST",
            #         "REQUEST_PATH": "https://10.15.0.110:443/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/nac-fabric1/config-deploy?forceShowRun=false", # noqa: E501
            #         "MESSAGE": "OK",
            #         "DATA": {
            #         "status": "Configuration deployment completed."
            #         }
            #     },
            #     "invocation": {
            #         "module_args": {
            #         "method": "POST",
            #         "path": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/nac-fabric1/config-deploy?forceShowRun=false", # noqa: E501
            #         "data": "None"
            #         }
            #     },
            #     "_ansible_parsed": true
            # }
            if ndfc_deploy.get('response'):
                if ndfc_deploy['response']['RETURN_CODE'] == 200:
                    results['changed'] = True

            # Failed response:
            # {
            #     "failed": true,
            #     "msg":{
            #         "RETURN_CODE": 400,
            #         "METHOD": "PUT",
            #         "REQUEST_PATH": "https://10.15.0.110:443/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/nac-fabric1/config-deploy?forceShowRun=false", # noqa: E501
            #         "MESSAGE": "Bad Request",
            #         "DATA": {
            #             "path": "rest/control/fabrics/nac-fabric1/config-deploy?forceShowRun=false",
            #             "Error": "Bad Request Error",
            #             "message": "", # noqa: E501
            #             "timestamp": "2025-02-24 13:49:41.024",
            #             "status": "400"
            #         }
            #     },
            #     "invocation": {
            #         "module_args": {
            #         "method": "POST",
            #         "path": "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/nac-fabric1/config-deploy?forceShowRun=false", # noqa: E501
            #         "data": "None"
            #         }
            #     },
            #     "_ansible_parsed": true
            # }
            if ndfc_deploy.get('msg'):
                if ndfc_deploy['msg']['RETURN_CODE'] != 200:
                    results['failed'] = True
                    results['msg'] = f"For fabric {fabric}; {ndfc_deploy['msg']['DATA']['message']}"

        return results

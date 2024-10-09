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

from ansible.plugins.action import ActionBase
import json
import re


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False
        results['poap_data'] = {}

        # Get data from Ansible task parameters
        model_data = self._task.args["model_data"]
        fabric_name = model_data['vxlan']['global']['name']
        switches = model_data['vxlan']['topology']['switches']

        # Check model switch data to see if any switches
        # have poap settings enabled
        poap_supported_switches = False
        for switch in switches:
            if 'poap' in switch and switch['poap'].get('bootstrap'):
                poap_supported_switches = True

        # If the data model does not enable poap we are done
        if not poap_supported_switches:
            return results

        # If we get here we need to query NDFC to see if any devices
        # show up in the poap (bootstrap) device list.
        parsed_data = []
        if poap_supported_switches:
            fabric_name = 'nac-ndfc1'
            poap_data = self._execute_module(
                module_name="cisco.dcnm.dcnm_rest",
                module_args={
                    "method": "GET",
                    "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/{fabric_name}/inventory/poap"
                },
                task_vars=task_vars,
                tmp=tmp
            )

            if poap_data.get('response'):
                if poap_data['response']['RETURN_CODE'] == 200:
                    parsed_data = self._parse_poap_data(poap_data['response']['DATA'])
            elif poap_data.get('failed'):
                # If we get here it's possible that the Fabric settings for
                # bootstrap are not enabled.  If that is the case we don't want
                # to error but rather just silently ignore it because the fabric
                # setting for this might be modified when the create role runs.
                fail_msg = poap_data.get('msg').get('DATA')
                match_text = r"Please\s+enable\s+the\s+DHCP\s+in\s+Fabric\s+Settings\s+to\s+start\s+the\s+bootstrap"
                if re.search(match_text, fail_msg, re.IGNORECASE):
                    pass
                else:
                    # Return any messages we don't recognize and fail
                    results['failed'] = True
                    results['message'] = "Unrecognized Failure Attempting To Get POAP Data: {0}".format(fail_msg)
                    return results

        if parsed_data:
            results['poap_data'] = parsed_data
        else:
            # Since POAP is enabled on at least one device in the service
            # model then we should not continue until we have POAP data
            # from NDFC
            results['failed'] = True
            msg1 = "POAP is enabled on at least one switch in the service model but "
            msg2 = "POAP bootstrap data is not yet available from NDFC. "
            msg3 = "To disable poap on a device set (poap.boostrap) to (False) under (vxlan.topology.switches)"
            results['message'] = msg1 + msg2 + msg3
            return results


        return results

    def _parse_poap_data(self, poap_data):
        # Helper function to parse the following data into a dict strucuture keyed on serial number
        #
        # [{'data': '{"gateway": "10.15.9.1/24", "modulesModel": ["N9K-X9364v", "N9K-vSUP"]}',
        #   'fingerprint': 'MD5:eb:c9:87:d9:13:8a:5d:06:04:0e:23:c8:a5:8c:d2:77',
        #   'model': 'N9K-C9300v',
        #   'publicKey': 'ssh-rsa AAAAB3<snip>',
        #   'reAdd': False,
        #   'seedSwitchFlag': False,
        #   'serialNumber': '9Y0K4YPFV64',
        #   'version': '9.3(8)'}]
        #

        parsed_poap_data = {}
        for switch in poap_data:
            parsed_poap_data[switch['serialNumber']] = {}
            parsed_poap_data[switch['serialNumber']]['model'] = switch['model']
            parsed_poap_data[switch['serialNumber']]['version'] = switch['version']
            parsed_poap_data[switch['serialNumber']]['gateway'] = self._split_string_data(switch['data'])['gateway']
            parsed_poap_data[switch['serialNumber']]['modulesModel'] = self._split_string_data(switch['data'])['modulesModel']
            parsed_poap_data[switch['serialNumber']]['serialNumber'] = switch['serialNumber']


        return parsed_poap_data

    def _split_string_data(self, switch_data):
        # Helper function to parse <class 'ansible.utils.unsafe_proxy.AnsibleUnsafeText'>
        # string data into a proper python dictionary
        #
        try:
            parsed = json.loads(switch_data)
        except json.JSONDecodeError:
            # If the switch_data does not parse properly create a dict
            # with the keys and data value 'NOT_SET'
            parsed = {}
            parsed['gateway'] = "NOT_SET"
            parsed['modulesModel'] = "NOT_SET"

        return parsed

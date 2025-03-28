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

        local_vpc_domain = self._task.args['data_source_vpc_domain']
        remote_vpc_domain = self._task.args['remote_vpc_domain']

        # Checking if Domain ID on NDFC is the same in the data_model to detect if we try to change domain
        for r_vpc in remote_vpc_domain:
            vpc_domain_id = self.check_local(r_vpc["entityName"], local_vpc_domain)
            if vpc_domain_id == r_vpc["allocatedIp"]:
                pass
            else:
                results['failed'] = True
                results['msg'] = "Domain ID in NDFC: "+r_vpc["allocatedIp"]+" is different than the data source."

        return results

    def check_local(self, entity, local_vpc_domain):
        for l_vpc in local_vpc_domain:
            # Create reverse entity in case it was build in an other order
            # SN_A~SN_B or SN_B~SN_A
            entity_tmp = l_vpc["entity_name"].split("~")
            rev_entity = entity_tmp[1]+"~"+entity_tmp[0]
            if l_vpc["entity_name"] == entity or rev_entity == entity:
                return l_vpc["resource"]
        return None
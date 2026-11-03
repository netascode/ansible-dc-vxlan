# Copyright (c) 2026 Cisco Systems, Inc. and its affiliates
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

"""
Validate the collection's boolean control flags before any controller change.

Extra vars passed as '-e key=value' are strings, so e.g. 'interface_delete_mode=false'
would otherwise be truthy in Python and enable deletion. Every public control flag is
rendered and strictly converted here; an invalid value fails the play early with the
flag name, even if the step that consumes the flag would later be skipped.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import (
    CONTROL_FLAGS,
    task_var_to_bool,
)


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        task_vars = task_vars or {}

        try:
            flags = {flag: task_var_to_bool(self._templar, task_vars, flag, False) for flag in CONTROL_FLAGS}
        except AnsibleError as e:
            results['failed'] = True
            results['msg'] = str(e)
            return results

        results['changed'] = False
        results['control_flags'] = flags
        return results

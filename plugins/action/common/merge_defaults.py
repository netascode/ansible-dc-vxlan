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

import os

import yaml

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail


def merge_dicts(d1, d2):
    for k, v in d2.items():
        if k in d1 and isinstance(d1[k], dict) and isinstance(v, dict):
            d1[k] = merge_dicts(d1[k], v)
        else:
            d1[k] = v
    return d1


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        task_vars = task_vars or {}
        results['failed'] = False
        results['msg'] = None

        defaults_file = self._task.args['defaults_file']

        factory_defaults = {}
        if os.path.exists(defaults_file):
            with open(defaults_file, 'r') as file_handle:
                loaded = yaml.load(file_handle, Loader=SafeLoader) or {}
            factory_defaults = loaded.get('factory_defaults') or {}

        # Read the validated model straight from task_vars instead of passing
        # data_model['data'] as a templated arg: templating the multi-MB model
        # through Jinja for every run costs several seconds.
        data_model = task_vars.get('data_model')
        if not isinstance(data_model, dict):
            raise AnsibleActionFail("merge_defaults requires the 'data_model' fact to be registered")
        model = data_model.get('data') or {}

        custom_defaults = {}
        if model.get('defaults') is not None:
            custom_defaults = model['defaults']

        results['defaults'] = merge_dicts(factory_defaults, custom_defaults)

        return results

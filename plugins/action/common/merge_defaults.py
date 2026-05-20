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

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase

display = Display()


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
        results["failed"] = False
        results["msg"] = None
        results["defaults"] = None
        results["factory_defaults"] = None

        factory_defaults = self._task.args.get("factory_defaults")
        factory_defaults_file = self._task.args.get("factory_defaults_file")
        data_model = self._task.args["data_model"]

        if factory_defaults is None and factory_defaults_file:
            defaults_path = factory_defaults_file
            if not os.path.isabs(defaults_path):
                role_path = task_vars.get("role_path", "")
                defaults_path = os.path.join(role_path, defaults_path)

            if os.path.isfile(defaults_path):
                with open(defaults_path, "r") as f:
                    loaded = yaml.safe_load(f) or {}
                factory_defaults = loaded.get("factory_defaults", loaded)
            else:
                factory_defaults = {}
        elif factory_defaults is None:
            factory_defaults = {}

        results["factory_defaults"] = factory_defaults

        cus_def = {}
        if data_model is not None:
            if data_model.get("defaults") is not None:
                cus_def = data_model["defaults"]

        results["defaults"] = merge_dicts(factory_defaults, cus_def)

        return results

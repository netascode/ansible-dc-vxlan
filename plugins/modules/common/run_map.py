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


DOCUMENTATION = """
---
module: run_map
short_description: Action plugin used to perform updates to run map for tracking previous run state.
version_added: "0.3.0"
author: Mike Wiebe (@mikewiebe)
description:
- Action plugin used to perform updates to run map for tracking previous run state.
options:
    schema:
        description:
        - The path to the schema file.
        required: false
        type: str
    mdata:
        description:
        - The path to the model data dir.
        required: true
        type: dict
    rules:
        description:
        - The path to the rules dir.
        required: false
        type: str
"""

EXAMPLES = """

# Used to perform updates to run map for tracking previous run state

- name: Mark Stage Role Create Completed
  cisco.nac_dc_vxlan.common.run_map:
    stage: role_create_completed
  register: run_map

"""

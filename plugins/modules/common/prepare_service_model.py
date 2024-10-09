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
module: prepare_service_model
short_description: Prepare action plugin to prepare extended runtime data model.
version_added: "0.1.0"
author: Mike Wiebe
description:
- Prepare action plugin to prepare extended runtime data model.
- Additional prepare action plugins are invoked for different parts of the data model.
options:
    inventory_hostname:
        description:
        - Ansible inventory_hostname.
        required: true
        type: str
    hostvars:
        description:
        - Ansible runtime hostvars data.
        required: true
        type: dict
    model_data:
        description:
        - The path to the data dir.
        required: true
        type: str
"""

EXAMPLES = """

# # Prepare Data Model and Return Extended Data Model

- name: Perform Required Syntax and Semantic Model Validation
  cisco.nac_dc_vxlan.common.prepare_service_model:
    inventory_hostname: "{{ inventory_hostname }}"
    hostvars: "{{ hostvars }}"
    model_data: "{{ model_data['data'] }}"
  register: smd

"""

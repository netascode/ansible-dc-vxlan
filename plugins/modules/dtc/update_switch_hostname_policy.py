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
module: update_switch_hostname_policy
short_description: Action plugin to parse, build, and return an updated policy payload for updating NDFC switch hostnames based on the data model.
version_added: "0.3.0"
author: Matt Tarkington (@mtarking)
description:
- Action plugin to parse, build, and return an updated policy payload for updating NDFC switch hostnames based on the data model.
options:
    mdata:
        description:
        - The runtime data model, typically the extended data model.
        required: true
        type: dict
    switch_serial_numbers:
        description:
        - List of switch serial numbers NDFC is managing.
        required: true
        type: list
        elements: str
    template_name:
        description:
        - NDFC template name.
        required: true
        type: str
"""

EXAMPLES = """

# Parses, builds, and returns an updated policy payload for updating NDFC switch hostnames based on the data model.

- name: Build Switch Hostname Policy Payload from Data Model Update
  cisco.nac_dc_vxlan.dtc.update_switch_hostname_policy:
    model_data: "{{ MD_Extended }}"
    switch_serial_numbers: "{{ md_serial_numbers }}"
    template_name: host_11_1

"""

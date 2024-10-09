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
module: get_credentials
short_description: Action plugin to get NDFC switch credentials and update inventory list.
version_added: "0.1.0"
author: Mike Wiebe (@mikewiebe)
description:
- Action plugin to get NDFC switch credentials and update inventory list.
options:
    inv_list:
        description:
        - Inventory list.
        required: true
        type: str
"""

EXAMPLES = """

# Get Collection NDFC Switch Credentials and Update Inventory List

- name: Retrieve NDFC Device Username and Password from Group Vars and update inv_config
  cisco.nac_dc_vxlan.common.get_credentials:
    inv_list: "{{ inv_config }}"
  register: updated_inv_config
  no_log: true

"""
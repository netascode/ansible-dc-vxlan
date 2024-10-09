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
module: verify_tags
short_description: Action plugin to verify embedded collection tags.
version_added: "0.3.0"
author: Mike Wiebe (@mikewiebe)
description:
- Action plugin to verify embedded collection tags.
- Used a dependency within the overall collection.
options:
    all_tags:
        description:
        - All the tags supported in the collection natively.
        required: true
        type: dict
    play_tags:
        description:
        - List of current play tags.
        required: true
        type: list
"""

EXAMPLES = """

# Perform Required Syntax and Semantic Model Validation and Return the Model Data

- name: Verify User Tags
  cisco.nac_dc_vxlan.dtc.verify_tags:
    all_tags: "{{ nac_tags.all }}"
    play_tags: "{{ ansible_run_tags }}"
  tags: "{{ ansible_run_tags }}"

"""
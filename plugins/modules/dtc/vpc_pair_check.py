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
module: nac_dc_validate
short_description: Prepare action plugin to validate the data model against the schema and return the rendered data model.
version_added: "0.1.0"
author: Rameez Rahim M (@rrahimm)
description:
- Prepare action plugin to validate the data model against the schema and return the rendered data model.
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

# Perform Required Syntax and Semantic Model Validation and Return the Model Data

- name: Perform Required Syntax and Semantic Model Validation
  cisco.nac_dc_vxlan.common.nac_dc_validate:
    schema: "{{ schema_path }}"
    mdata: "{{ data_path }}"
    rules: "{{ rules_path }}"
  register: model_data

"""

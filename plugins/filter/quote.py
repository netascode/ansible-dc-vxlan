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

DOCUMENTATION = r"""
  name: quote
  version_added: "0.4.0"
  short_description: Quote
  description:
    - Quote a string or integer.
  positional: item
  options:
    item:
      description: Item to quote.
      required: true
"""

EXAMPLES = r"""

    quoted: "{{ var1 | cisco.nac_dc_vxlan.quote() }}"
    # => True

"""

RETURN = r"""
  _value:
    description:
      - A string value.
    type: str
"""

import operator
from jinja2.runtime import Undefined
from jinja2.exceptions import UndefinedError

from packaging.version import Version

from ansible.module_utils.six import string_types
from ansible.errors import AnsibleFilterError, AnsibleFilterTypeError
from ansible.module_utils.common.text.converters import to_native


def quote(item):
    # if not isinstance(version1, (string_types, Undefined)):
    #     raise AnsibleFilterTypeError(f"Can only check string versions, however version1 is: {type(version1)}")

    # if not isinstance(version2, (string_types, Undefined)):
    #     raise AnsibleFilterTypeError(f"Can only check string versions, however version2 is: {type(version2)}")

    # if not isinstance(op, (string_types, Undefined)) and op not in SUPPORTED_COMPARISON_OPERATORS:
    #     raise AnsibleFilterError(f"Unsupported operator {op} type. Supported operators are: {SUPPORTED_COMPARISON_OPERATORS}")

    try:
        return f'"{item}"'
    except UndefinedError:
        raise
    except Exception as e:
        raise AnsibleFilterError("Unable handle version: %s" % to_native(e), orig_exc=e)


# ---- Ansible filters ----
class FilterModule(object):
    """ Quote filter """

    def filters(self):
        return {
            "quote": quote
        }

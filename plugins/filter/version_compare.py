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
  name: version_compare
  version_added: "0.3.0"
  short_description: Compare version
  description:
    - Compare version between two different versions.
  positional: version1, version2
  options:
    version1:
      description: First version to compare.
      type: str
      required: true
    version2:
      description: Second version to compare.
      type: str
      required: true
    op:
      description: Comparison operator.
      type: str
      required: true
"""

EXAMPLES = r"""

version_compare_result: "{{ '1.0.2' | cisco.nac_dc_vxlan.version_compare('1.0.1', '>') }}"
# => True

# {% if ndfc_version.response.DATA.version | cisco.nac_dc_vxlan.version_compare('12.2.2', '>=') %}

# - ansible.builtin.set_fact:
#     version_compare_result: "{{ '1.0.2' | cisco.nac_dc_vxlan.version_compare('1.0.1', '>=') }}"
#   when: MD_Extended.vxlan.global
#   delegate_to: localhost
"""

RETURN = r"""
  _value:
    description:
      - A boolean value.
    type: bool
"""

import operator
from jinja2.runtime import Undefined
from jinja2.exceptions import UndefinedError

try:
    from packaging.version import Version
except ImportError as imp_exc:
    PACKAGING_LIBRARY_IMPORT_ERROR = imp_exc
else:
    PACKAGING_LIBRARY_IMPORT_ERROR = None

from ansible.module_utils.six import string_types
from ansible.errors import AnsibleError, AnsibleFilterError, AnsibleFilterTypeError
from ansible.module_utils.common.text.converters import to_native


SUPPORTED_COMPARISON_OPERATORS = ['==', '!=', '>', '>=', '<', '<=']


def version_compare(version1, version2, op):
    """
    Compare two version strings using the specified operator.
    Args:
        version1 (str): The first version string to compare.
        version2 (str): The second version string to compare.
        op (str): The comparison operator as a string. Supported: '==', '!=', '>', '>=', '<', '<='.
    Returns:
        bool: The result of the comparison.
    Raises:
        AnsibleError: If the 'packaging' library is not installed.
        AnsibleFilterTypeError: If the version arguments are not strings.
        AnsibleFilterError: If the operator is unsupported or version parsing fails.
    """
    if PACKAGING_LIBRARY_IMPORT_ERROR:
        raise AnsibleError('packaging must be installed to use this filter plugin') from PACKAGING_LIBRARY_IMPORT_ERROR

    if not isinstance(version1, (string_types, Undefined)):
        raise AnsibleFilterTypeError(f"Can only check string versions, however version1 is: {type(version1)}")

    if not isinstance(version2, (string_types, Undefined)):
        raise AnsibleFilterTypeError(f"Can only check string versions, however version2 is: {type(version2)}")

    if not isinstance(op, (string_types, Undefined)) and op not in SUPPORTED_COMPARISON_OPERATORS:
        raise AnsibleFilterError(f"Unsupported operator {op} type. Supported operators are: {SUPPORTED_COMPARISON_OPERATORS}")

    try:
        v1 = Version(version1)
        v2 = Version(version2)
    except UndefinedError:
        raise
    except Exception as e:
        raise AnsibleFilterError("Unable handle version: %s" % to_native(e), orig_exc=e)

    if op == '==':
        return operator.eq(v1, v2)
    elif op == '!=':
        return operator.ne(v1, v2)
    elif op == '>':
        return operator.gt(v1, v2)
    elif op == '>=':
        return operator.ge(v1, v2)
    elif op == '<':
        return operator.lt(v1, v2)
    elif op == '<=':
        return operator.le(v1, v2)
    else:
        raise AnsibleFilterError(f"Unsupported operator {op} type. Supported operators are: {SUPPORTED_COMPARISON_OPERATORS}")


# ---- Ansible filters ----
class FilterModule(object):
    """ Version compare filter """

    def filters(self):
        return {
            "version_compare": version_compare
        }

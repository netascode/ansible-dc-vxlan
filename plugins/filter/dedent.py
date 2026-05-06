# Copyright (c) 2026 Cisco Systems, Inc. and its affiliates
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
  name: dedent
  version_added: "0.8.0"
  short_description: Remove common leading whitespace from text
  description:
    - Remove common leading whitespace from every line in the input text.
    - Useful for normalizing multiline strings defined with YAML block scalars (|2, |, etc.).
  positional: text
  options:
    text:
      description: The text to dedent.
      type: str
      required: true
"""

EXAMPLES = r"""

# Basic usage - remove common leading whitespace
dedented_text: "{{ my_multiline_var | cisco.nac_dc_vxlan.dedent }}"

# Combine with indent to normalize and re-indent
normalized_config: "{{ ibgp_template | cisco.nac_dc_vxlan.dedent | indent(6, true) }}"
"""

RETURN = r"""
  _value:
    description:
      - The dedented string with common leading whitespace removed.
    type: str
"""

import textwrap

from ansible.module_utils.six import string_types
from ansible.errors import AnsibleFilterError, AnsibleFilterTypeError
from ansible.module_utils.common.text.converters import to_native
from jinja2.runtime import Undefined
from jinja2.exceptions import UndefinedError


def dedent(text):
    """
    Remove common leading whitespace from every line in text.
    Args:
        text (str): The text string to dedent.
    Returns:
        str: The dedented text.
    Raises:
        AnsibleFilterTypeError: If the text argument is not a string.
        AnsibleFilterError: If the dedent operation fails.
    """
    if isinstance(text, Undefined):
        return text

    if text is None:
        return ""

    if not isinstance(text, string_types):
        raise AnsibleFilterTypeError(f"dedent requires a string, got: {type(text)}")

    if not text:
        return text

    try:
        return textwrap.dedent(text)
    except UndefinedError:
        raise
    except Exception as e:
        raise AnsibleFilterError("Unable to dedent text: %s" % to_native(e), orig_exc=e)


# ---- Ansible filters ----
class FilterModule(object):
    """ Dedent filter - remove common leading whitespace """

    def filters(self):
        return {
            "dedent": dedent
        }

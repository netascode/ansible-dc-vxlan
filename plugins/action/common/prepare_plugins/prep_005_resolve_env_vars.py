# Copyright (c) 2025 Cisco Systems, Inc. and its affiliates
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

import os
import re
from ansible.utils.display import Display

display = Display()

ENV_VAR_PREFIX = 'env_var_'

# Matches env_var_ followed by one or more word characters (a-z, A-Z, 0-9, _)
ENV_VAR_PATTERN = re.compile(r'env_var_\w+')


def resolve_env_var_token(token, path):
    """
    Resolve a single env_var_ token to its environment variable value.

    Note: Environment variables containing special characters like $, `, \\, etc.
    should be properly escaped when setting them in the shell.
    Example: export BGP_AUTH_KEY='MyP@$$w0rd' (use single quotes to prevent shell interpretation)
    """
    resolved = os.getenv(token)

    if resolved is None:
        display.warning(
            f"Environment variable '{token}' referenced at "
            f"'{path}' is not set. The value will not be resolved."
        )
        return token

    display.vvv(f"Resolved '{token}' from environment variable at '{path}'")
    return resolved


def resolve_env_vars_in_string(value, path):
    resolved_count = 0

    def replace_match(match):
        nonlocal resolved_count
        token = match.group(0)
        replacement = resolve_env_var_token(token, path)
        if replacement != token:
            resolved_count += 1
        return replacement

    new_value = ENV_VAR_PATTERN.sub(replace_match, value)
    return new_value, resolved_count


def resolve_env_vars_recursive(data, path=''):
    resolved_count = 0

    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            if isinstance(value, str) and ENV_VAR_PREFIX in value:
                data[key], count = resolve_env_vars_in_string(value, current_path)
                resolved_count += count
            elif isinstance(value, (dict, list)):
                resolved_count += resolve_env_vars_recursive(value, current_path)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            current_path = f"{path}[{index}]"
            if isinstance(item, str) and ENV_VAR_PREFIX in item:
                data[index], count = resolve_env_vars_in_string(item, current_path)
                resolved_count += count
            elif isinstance(item, (dict, list)):
                resolved_count += resolve_env_vars_recursive(item, current_path)

    return resolved_count


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        data_model = self.kwargs['results']['model_extended']

        resolved_count = resolve_env_vars_recursive(data_model)
        if resolved_count > 0:
            display.v(f"Resolved {resolved_count} environment variable(s) in the data model")

        self.kwargs['results']['model_extended'] = data_model
        return self.kwargs['results']

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


class UnresolvedEnvVarError(Exception):
    """
    Raised when an env_var_ token cannot be resolved to an environment
    variable at runtime. This is a fail-closed guard that prevents a literal
    env_var_ token from being sent to NDFC as configuration data.
    """
    pass


def resolve_env_var_token(token, path):
    """
    Resolve a single env_var_ token to its environment variable value.

    Fails closed: if the environment variable is not set, raises
    UnresolvedEnvVarError instead of returning the literal token. This
    guarantees that a missing secret can never be submitted to NDFC as an
    executable credential value.

    Note: Environment variables containing special characters like $, `, \\, etc.
    should be properly escaped when setting them in the shell.
    Example: export BGP_AUTH_KEY='MyP@$$w0rd' (use single quotes to prevent shell interpretation)
    """
    resolved = os.getenv(token)

    if resolved is None:
        raise UnresolvedEnvVarError(
            f"Environment variable '{token}' referenced at '{path}' is not set."
        )

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
    """
    Resolve all env_var_ tokens in a data structure by replacing them
    with the corresponding environment variable values (in-place).

    Used at runtime by build_resource_data to resolve tokens in
    module_data (a deep copy) before sending to NDFC modules.
    """
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


def validate_env_vars_recursive(data, path='', missing=None, validated=None):
    """
    Walk the data structure and validate that all env_var_ tokens have
    corresponding environment variables set, without resolving them.

    Tokens remain as-is in the data so that rendered files do not
    contain secrets. Runtime resolution happens in build_resource_data.

    Aggregates every missing token together with its data model path into
    the ``missing`` list so the caller can fail closed with a single,
    complete error message rather than a stream of warnings that are easy
    to lose in automation output.

    Returns:
        (validated_count, missing) where ``missing`` is a list of
        (token, path) tuples for every referenced env var that is not set.
    """
    if missing is None:
        missing = []
    if validated is None:
        validated = [0]

    def _check(value, current_path):
        for match in ENV_VAR_PATTERN.finditer(value):
            token = match.group(0)
            if os.getenv(token) is None:
                missing.append((token, current_path))
            else:
                display.vvv(
                    f"Validated '{token}' exists as environment variable at '{current_path}'"
                )
                validated[0] += 1

    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            if isinstance(value, str) and ENV_VAR_PREFIX in value:
                _check(value, current_path)
            elif isinstance(value, (dict, list)):
                validate_env_vars_recursive(value, current_path, missing, validated)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            current_path = f"{path}[{index}]"
            if isinstance(item, str) and ENV_VAR_PREFIX in item:
                _check(item, current_path)
            elif isinstance(item, (dict, list)):
                validate_env_vars_recursive(item, current_path, missing, validated)

    return validated[0], missing


class PreparePlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        data_model = self.kwargs['results']['model_extended']

        # Fail closed: stop here (during validate, before any rendering or NDFC
        # mutation) if any referenced env var is missing, so a literal env_var_
        # token can never reach NDFC as a credential value. Tokens are kept as
        # placeholders; runtime resolution happens in build_resource_data.
        validated_count, missing = validate_env_vars_recursive(data_model)

        if missing:
            lines = "\n".join(
                f"  - '{token}' referenced at '{path}'" for token, path in missing
            )
            self.kwargs['results']['failed'] = True
            self.kwargs['results']['msg'] = (
                f"{len(missing)} environment variable(s) referenced in the data "
                f"model with the '{ENV_VAR_PREFIX}' prefix are not set:\n{lines}\n"
                "The run is stopped to avoid sending unresolved tokens to Nexus Dashboard."
            )
            return self.kwargs['results']

        if validated_count > 0:
            display.v(f"Validated {validated_count} environment variable(s) in the data model")

        self.kwargs['results']['model_extended'] = data_model
        return self.kwargs['results']

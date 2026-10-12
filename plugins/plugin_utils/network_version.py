# Copyright (c) 2026 Cisco Systems, Inc. and its affiliates
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# SPDX-License-Identifier: MIT

"""Resolve the network module's version control from controller discovery."""

import re


IPV4_ACL_IN_SMU_VERSION = "4.3.1.0175006011"


def _numeric_component(value):
    """Return a canonical nonnegative version component, or None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value) if value >= 0 else None
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value.strip()):
        return str(int(value.strip()))
    return None


def resolve_network_patch_version(nd_smu_versions=None, nd_version=None, nd_version_response=None):
    """Select a compatible active SMU, otherwise the discovered numeric ND release.

    SMU discovery returns a list of active versions, with no capability or
    release ordering. Only the SMU supported by the base network module takes
    precedence; unrelated SMUs must not hide a supported ND release.

    Prefer /version.json's major/minor/maintenance fields. Keep the full
    nd_version fact unchanged for consumers that use its patch letter, while
    providing numeric components to dcnm_network. When only the full fact is
    available, accept its numeric release and optional patch letter/build.

    Older numeric releases are also returned so the base module can report its
    version requirement when an ACL is requested. Unknown versions return None;
    neither NDFC's application version nor an inventory override is used.
    """
    if isinstance(nd_smu_versions, (list, tuple)) and IPV4_ACL_IN_SMU_VERSION in nd_smu_versions:
        return IPV4_ACL_IN_SMU_VERSION

    if isinstance(nd_version_response, dict):
        version_json = nd_version_response.get("json")
        if isinstance(version_json, dict):
            components = [_numeric_component(version_json.get(key)) for key in ("major", "minor", "maintenance")]
            if all(component is not None for component in components):
                return ".".join(components)

    if not isinstance(nd_version, str):
        return None
    match = re.fullmatch(r"([0-9]+)\.([0-9]+)\.([0-9]+)(?:[a-zA-Z]|(?:\.[0-9]+)+)?", nd_version.strip())
    if match is None:
        return None
    return ".".join(str(int(component)) for component in match.groups())

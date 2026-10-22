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


IPV4_ACL_IN_SMU_VERSION = "4.3.1.0175006017"

# Capability signal passed to dcnm_network/dcnm_interface when the SMU patch is
# active. The patch enables a family of features (network ipv4_acl_in, interface
# extended properties, ...), not just one. NaC verifies the SMU; the module
# trusts this fixed value (it is a local control arg, not sent to ND).
PATCH_VERSION = "4.4.1"


def resolve_network_patch_version(nd_patch_enabled=False, **_ignored):
    """Return the patch_version capability signal when the SMU patch is active, else None.

    The env-var lookup and exact active-SMU match are performed once in the
    connectivity_check role, which exposes the boolean ``nd_patch_enabled``
    fact. This resolver maps that single decision to the fixed ``"4.4.1"``
    capability signal the base modules accept, or ``None`` to omit the argument
    entirely. ``None`` is an internal omit indicator only; it must never be
    forwarded as ``patch_version: null``.

    The former numeric-release fallback and fixed-SMU-literal path are removed:
    the configured SMU alone determines eligibility.
    """
    return PATCH_VERSION if nd_patch_enabled else None


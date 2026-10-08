# Copyright (c) 2026 Cisco Systems, Inc. and its affiliates
# SPDX-License-Identifier: MIT

"""Check SMU-first selection and normalization of controller ND versions."""

import pytest

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.network_version import resolve_network_patch_version


SMU_VERSION = "4.3.1.0175006011"


@pytest.mark.parametrize("smus", [
    [SMU_VERSION],
    ["4.3.1.10", SMU_VERSION, "4.3.1.99"],
    [SMU_VERSION, "4.3.1.10"],
    ("4.3.1.99", SMU_VERSION),
])
def test_supported_smu_precedes_nd_release(smus):
    raw_version = {"json": {"major": 5, "minor": 1, "maintenance": 1}}
    assert resolve_network_patch_version(smus, "4.4.1", raw_version) == SMU_VERSION


@pytest.mark.parametrize("smus", [
    None, [], ["4.3.1.0175006012"], [None, 123, "unrelated"],
    SMU_VERSION, {SMU_VERSION: True}, [" " + SMU_VERSION],
])
def test_only_exact_smu_in_supported_container_enables_patch(smus):
    assert resolve_network_patch_version(smus, "4.3.1") == "4.3.1"


@pytest.mark.parametrize("version,expected", [
    ("4.4.1", "4.4.1"),
    ("4.4.1a", "4.4.1"),
    ("4.4.1Z", "4.4.1"),
    ("4.5.2.10.4", "4.5.2"),
    ("04.004.001", "4.4.1"),
    ("3.2.2m", "3.2.2"),
    ("4.3.1", "4.3.1"),
])
def test_nd_release_normalization_preserves_older_releases(version, expected):
    assert resolve_network_patch_version(nd_version=version) == expected


@pytest.mark.parametrize("version", [
    None, "", True, 4, 4.4, [], {}, "4.4", "-4.4.1", "4.4.-1",
    "4.4.1ab", "4.4.1.10a", "4.4.1-rc1", "4.4(1)", "4.4.١",
])
def test_malformed_nd_version_cannot_enable_patch(version):
    assert resolve_network_patch_version(nd_version=version) is None


@pytest.mark.parametrize("parts,expected", [
    ((4, 4, 1), "4.4.1"),
    ((" 04 ", "004", "001"), "4.4.1"),
    ((0, 0, 0), "0.0.0"),
])
def test_version_json_components_precede_fallback(parts, expected):
    raw = {"json": dict(zip(("major", "minor", "maintenance"), parts))}
    assert resolve_network_patch_version(nd_version="5.1.1", nd_version_response=raw) == expected


@pytest.mark.parametrize("invalid_component", [None, True, -1, 4.1, "-1", "4.0", "", "٤", [], {}])
def test_invalid_raw_component_uses_valid_fallback(invalid_component):
    raw = {"json": {"major": invalid_component, "minor": 4, "maintenance": 1}}
    assert resolve_network_patch_version(nd_version="4.5.1", nd_version_response=raw) == "4.5.1"
    assert resolve_network_patch_version(nd_version="malformed", nd_version_response=raw) is None


@pytest.mark.parametrize("raw", [None, [], "unexpected", {}, {"json": None}, {"json": []}, {"json": {"major": 4}}])
def test_missing_or_malformed_raw_response_uses_fallback(raw):
    assert resolve_network_patch_version(nd_version="4.4.1", nd_version_response=raw) == "4.4.1"


def test_missing_discovery_facts_omit_module_control():
    assert resolve_network_patch_version() is None

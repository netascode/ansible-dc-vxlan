# Copyright (c) 2026 Cisco Systems, Inc. and its affiliates
# SPDX-License-Identifier: MIT

"""Exercise firmware response parsing and active SMU history without a controller."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase

from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.parse_nd_smu_versions import ActionModule


CURRENT_FIRMWARE = "4.3.1.12345"
ACL_SMU = "4.3.1.0175006011"
OTHER_SMU = "4.3.1.0175006000"
MISSING = object()


def event(action, timestamp=MISSING, version=ACL_SMU):
    smu = {"version": version, "action": action}
    if timestamp is not MISSING:
        smu["timestamp"] = timestamp
    return smu


def activity(smus, version=CURRENT_FIRMWARE):
    return {"fromVersion": version, "toVersion": version, "smus": smus}


@pytest.fixture
def run_parser():
    def run(smus=None, shape="list", history=None, data=MISSING, response=MISSING):
        if response is MISSING:
            if data is MISSING:
                firmware = {
                    "firmwareName": CURRENT_FIRMWARE,
                    "upgradeHistory": history if history is not None else [activity(smus or [])],
                }
                data = {"firmwares": [firmware]} if shape == "wrapped" else [firmware]
            response = {"response": {"RETURN_CODE": 200, "DATA": data}}
        action = ActionModule.__new__(ActionModule)
        action._task = SimpleNamespace(args={"response": response})
        with patch.object(ActionBase, "run", return_value={}):
            result = action.run(task_vars={})
        assert result["changed"] is False
        return result["smu_versions"]

    return run


@pytest.mark.parametrize("shape", ["wrapped", "list"])
def test_response_shapes_return_all_active_smus(run_parser, shape):
    versions = run_parser(
        [event("activate", version=ACL_SMU), event("activate", version=OTHER_SMU)],
        shape=shape,
    )
    assert versions == sorted([ACL_SMU, OTHER_SMU])


def test_only_current_firmware_smu_activity_is_used(run_parser):
    history = [
        activity([event("activate", version="old-firmware-smu")], version="4.1.1.12345"),
        {"fromVersion": "4.1.1.12345", "toVersion": CURRENT_FIRMWARE,
         "smus": [event("activate", version="upgrade-transition-smu")]},
        activity([event("activate")]),
    ]
    assert run_parser(history=history) == [ACL_SMU]


def test_unmatched_firmware_activity_returns_no_smus(run_parser):
    assert run_parser(history=[activity([event("activate")], version="4.1.1.12345")]) == []


@pytest.mark.parametrize("data", [None, [], {}, {"firmwares": []}, "unexpected"])
def test_absent_firmware_data_returns_no_smus(run_parser, data):
    assert run_parser(data=data) == []


def test_missing_upgrade_history_returns_no_smus(run_parser):
    assert run_parser(data=[{"firmwareName": CURRENT_FIRMWARE}]) == []


def test_activate_remove_reactivate_uses_latest_timestamp(run_parser):
    # History is deliberately not sorted by event timestamp.
    smus = [
        event("activate", "2026-10-08T12:00:00Z"),
        event("remove", "2026-10-08T11:00:00Z"),
        event("activate", "2026-10-08T10:00:00Z"),
    ]
    assert run_parser(smus) == [ACL_SMU]


@pytest.mark.parametrize("inactive_action", ["remove", "superseded"])
def test_latest_inactive_event_excludes_smu(run_parser, inactive_action):
    assert run_parser([
        event(inactive_action, "2026-10-08T12:00:00Z"),
        event("activate", "2026-10-08T11:00:00Z"),
    ]) == []


@pytest.mark.parametrize("timestamps", [(9, 10), (9.5, 10.5), (0, 1)])
def test_numeric_timestamps_are_compared_numerically(run_parser, timestamps):
    assert run_parser([event("remove", timestamps[1]), event("activate", timestamps[0])]) == []


def test_timezone_offsets_are_compared_as_instants(run_parser):
    # 10:00 at -04:00 is later than 12:00 UTC, despite its lexical clock value.
    assert run_parser([
        event("remove", "2026-10-08T12:00:00Z"),
        event("activate", "2026-10-08T10:00:00-04:00"),
    ]) == [ACL_SMU]


def test_naive_iso_timestamp_is_treated_as_utc(run_parser):
    assert run_parser([
        event("remove", "2026-10-08T12:00:00"),
        event("activate", "2026-10-08T10:00:00-04:00"),
    ]) == [ACL_SMU]


@pytest.mark.parametrize("timestamp", [MISSING, None, "not-a-timestamp", {}, True])
def test_unparseable_timestamps_use_later_list_event(run_parser, timestamp):
    assert run_parser([event("remove", timestamp), event("activate", timestamp)]) == [ACL_SMU]


@pytest.mark.parametrize("timestamp", [MISSING, None, "not-a-timestamp"])
@pytest.mark.parametrize("valid_first", [True, False])
def test_mixed_parseable_and_unparseable_timestamps_use_list_order(run_parser, timestamp, valid_first):
    valid_time = "2026-10-08T12:00:00Z"
    timestamps = (valid_time, timestamp) if valid_first else (timestamp, valid_time)
    assert run_parser([event("remove", timestamps[0]), event("activate", timestamps[1])]) == [ACL_SMU]


def test_missing_timestamp_establishes_list_order_fallback(run_parser):
    assert run_parser([
        event("activate", "2026-10-08T12:00:00Z"),
        event("remove"),
        event("remove", "2026-10-08T11:00:00Z"),
    ]) == []


def test_equal_timestamps_use_later_list_event(run_parser):
    timestamp = "2026-10-08T12:00:00Z"
    assert run_parser([event("remove", timestamp), event("activate", timestamp)]) == [ACL_SMU]


def test_incomplete_smu_events_are_ignored(run_parser):
    assert run_parser([None, {}, {"version": ACL_SMU}, {"action": "activate"}, event("activate")]) == [ACL_SMU]


@pytest.mark.parametrize("wrapper", ["response", "msg"])
def test_non_200_response_is_an_action_failure(run_parser, wrapper):
    with pytest.raises(AnsibleActionFail, match="got RETURN_CODE=403"):
        run_parser(response={wrapper: {"RETURN_CODE": 403, "DATA": {"error": "forbidden"}}})


def test_response_argument_is_required(run_parser):
    with pytest.raises(AnsibleActionFail, match="`response` argument is required"):
        run_parser(response=None)

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

from __future__ import absolute_import, division, print_function


__metaclass__ = type

from datetime import datetime, timezone


def extract_firmware(data):
    # The firmwares endpoint returns two shapes across ND versions:
    #   older builds -> {"firmwares": [ {...} ]}; ND >= 4.1 -> [ {...} ] directly.
    if isinstance(data, dict):
        firmwares = data.get("firmwares") or []
    elif isinstance(data, list):
        firmwares = data
    else:
        firmwares = []
    return firmwares[0] if firmwares else {}


def timestamp_key(timestamp):
    # Return a UTC datetime for an ISO string or numeric Unix seconds, else None
    # so the caller can fall back to event list order. Naive ISO is treated UTC.
    if isinstance(timestamp, bool):
        return None
    try:
        if isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(timestamp, timezone.utc)
        if not isinstance(timestamp, str):
            return None
        # Python 3.9's fromisoformat does not accept the UTC "Z" suffix.
        if timestamp.endswith("Z"):
            timestamp = timestamp[:-1] + "+00:00"
        parsed = datetime.fromisoformat(timestamp)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def collect_active_smus(upgrade_history, current_full_version):
    # Find the upgrade entry representing SMU activity on the running version
    # (fromVersion == toVersion == current), then keep each version only if its
    # latest event (by timestamp, list order breaking ties) is "activate".
    for upgrade in upgrade_history:
        if (upgrade.get("fromVersion") == current_full_version
                and upgrade.get("toVersion") == current_full_version):
            smus = upgrade.get("smus") or []
            latest = {}
            for smu in smus:
                if not smu:
                    continue
                version = smu.get("version")
                action = smu.get("action")
                if not version or not action:
                    continue
                event_time = timestamp_key(smu.get("timestamp"))
                existing = latest.get(version)
                if (existing is None or event_time is None or existing[0] is None
                        or event_time >= existing[0]):
                    latest[version] = (event_time, action)
            active = {
                version
                for version, (_event_time, action) in latest.items()
                if action == "activate"
            }
            return sorted(active)
    return []


def parse_smu_versions(response):
    # Parse a dcnm_rest firmwares response into a sorted list of active SMU
    # versions. Raises ValueError if RETURN_CODE is not 200. dcnm_rest wraps
    # success under "response" and error under "msg" depending on HTTP status.
    response = response or {}
    resp_dict = response.get("response") or {}
    msg_dict = response.get("msg") or {}
    return_code = resp_dict.get("RETURN_CODE") or msg_dict.get("RETURN_CODE") or 0
    if return_code != 200:
        raise ValueError(
            "Expected HTTP 200 from /api/v1/infra/systemSoftware/firmwares, "
            "got RETURN_CODE={0}. Response: {1}. Error: {2}".format(
                return_code, resp_dict, msg_dict
            )
        )
    firmware = extract_firmware(resp_dict.get("DATA"))
    upgrade_history = firmware.get("upgradeHistory") or []
    if not upgrade_history:
        return []
    current_full_version = firmware.get("firmwareName") or ""
    return collect_active_smus(upgrade_history, current_full_version)

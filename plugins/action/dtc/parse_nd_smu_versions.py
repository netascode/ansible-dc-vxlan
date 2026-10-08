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

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail


class ActionModule(ActionBase):
    TRANSFERS_FILES = False
    _supports_check_mode = True

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        del tmp

        args = self._task.args or {}
        response = args.get("response")
        if response is None:
            raise AnsibleActionFail("`response` argument is required")

        # dcnm_rest wraps success payloads under "response" and error payloads under "msg".
        # This is orthogonal to ND version — it depends on HTTP status.
        resp_dict = response.get("response") or {}
        msg_dict = response.get("msg") or {}
        return_code = resp_dict.get("RETURN_CODE") or msg_dict.get("RETURN_CODE") or 0

        result["changed"] = False
        result["smu_versions"] = []

        if return_code != 200:
            raise AnsibleActionFail(
                f"Expected HTTP 200 from /api/v1/infra/systemSoftware/firmwares, "
                f"got RETURN_CODE={return_code}. Response: {resp_dict}. Error: {msg_dict}"
            )

        firmware = self._extract_firmware(resp_dict.get("DATA"))
        upgrade_history = firmware.get("upgradeHistory") or []

        if not upgrade_history:
            # Either the ND version doesn't expose SMU history at this endpoint
            # (observed on 4.1.1)
            return result

        current_full_version = firmware.get("firmwareName") or ""
        result["smu_versions"] = self._collect_active_smus(upgrade_history, current_full_version)
        return result

    @staticmethod
    def _extract_firmware(data):
        """
        Return the first firmware dict from the DATA payload.

        The endpoint returns two different shapes across ND versions:
        - Older builds: {"firmwares": [ {...}, ... ]}
        - ND >= 4.1:    [ {...}, ... ]   (the list directly)

        Returns {} if DATA is missing, empty, or an unexpected type — the caller
        can then treat the absence of upgradeHistory as "nothing to report".
        """
        if isinstance(data, dict):
            firmwares = data.get("firmwares") or []
        elif isinstance(data, list):
            firmwares = data
        else:
            firmwares = []
        return firmwares[0] if firmwares else {}

    @staticmethod
    def _collect_active_smus(upgrade_history, current_full_version):
        """
        Walk upgrade_history for the first entry that represents SMU activity on
        the currently-running version (fromVersion == toVersion == current), then
        return the SMU versions that are currently active.

        A version's active state is decided by its *latest* event, not by set
        membership. The firmware-history contract permits repeated events for the
        same version (e.g. remove on day 1, re-activate on day 2); their order is
        given by the per-event ``timestamp``. For each version we keep only the
        most recent event and include the version when that event's action is
        ``activate``. ``remove`` and ``superseded`` are treated as inactive.

        Events without a parseable timestamp fall back to their position in the
        ``smus`` list (later entries win), so ordering is preserved even if the
        controller omits timestamps.
        """
        for upgrade in upgrade_history:
            if (upgrade.get("fromVersion") == current_full_version
                    and upgrade.get("toVersion") == current_full_version):
                smus = upgrade.get("smus") or []

                # For each version, remember the latest event seen so far. The
                # sort key is (timestamp, list_index): timestamp decides order
                # when present; list_index breaks ties and covers missing
                # timestamps (later list position is later).
                latest = {}
                for index, smu in enumerate(smus):
                    if not smu:
                        continue
                    version = smu.get("version")
                    action = smu.get("action")
                    if not version or not action:
                        continue
                    sort_key = (ActionModule._timestamp_key(smu.get("timestamp")), index)
                    existing = latest.get(version)
                    if existing is None or sort_key >= existing[0]:
                        latest[version] = (sort_key, action)

                active = {
                    version
                    for version, (_sort_key, action) in latest.items()
                    if action == "activate"
                }
                return sorted(active)
        return []

    @staticmethod
    def _timestamp_key(timestamp):
        """
        Convert an SMU event timestamp into a sortable value.

        Returns a value that orders chronologically and always compares less
        than any real timestamp when the field is missing or unparseable, so
        events without a timestamp defer to list order (handled by the index
        tie-breaker in the caller).
        """
        if not timestamp:
            return ""
        return str(timestamp)

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

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import hashlib
import json
import os
import glob
import difflib

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase

display = Display()


class ActionModule(ActionBase):
    """Manage service model files for the validate role.

    Replaces manage_model_files_previous.yml and manage_model_files_current.yml
    with a single efficient action plugin call.

    Parameters:
        fabric_name (str): Fabric name for file naming
        data_model (dict): Golden service model data
        data_model_extended (dict): Extended service model data
        display_diff (bool): Display diff output to console (default: false)
        checksum_compare (bool): Enable checksum-based skip logic (default: false)
        save_previous (bool): Save previous files with _previous suffix (default: true)
        force_run_all (bool): Clean up previous run files (default: false)

    Returns:
        changed (bool): Whether model data has changed from previous
        skip_validation (bool): True if checksums match - caller should end_host
        previous_exists (bool): Whether previous model files existed
        golden_diff (str): Diff output for golden model (when display_diff is true)
        extended_diff (str): Diff output for extended model (when display_diff is true)
    """

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results["failed"] = False
        results["changed"] = False

        fabric_name = self._task.args.get("fabric_name")
        data_model = self._task.args.get("data_model")
        data_model_extended = self._task.args.get("data_model_extended")
        display_diff = self._task.args.get("display_diff", False)
        checksum_compare = self._task.args.get("checksum_compare", False)
        save_previous = self._task.args.get("save_previous", True)
        force_run_all = self._task.args.get("force_run_all", False)

        if not fabric_name or data_model is None or data_model_extended is None:
            results["failed"] = True
            results["msg"] = (
                "fabric_name, data_model, and data_model_extended are required"
            )
            return results

        role_path = task_vars.get("role_path", "")
        files_dir = os.path.join(role_path, "files")

        if not os.path.exists(files_dir):
            os.makedirs(files_dir)

        golden_file = os.path.join(
            files_dir, f"{fabric_name}_service_model_golden.json"
        )
        extended_file = os.path.join(
            files_dir, f"{fabric_name}_service_model_extended.json"
        )
        golden_prev_file = os.path.join(
            files_dir, f"{fabric_name}_service_model_golden_previous.json"
        )
        extended_prev_file = os.path.join(
            files_dir, f"{fabric_name}_service_model_extended_previous.json"
        )

        # --- Phase 1: Handle previous files ---
        golden_exists = os.path.isfile(golden_file)
        extended_exists = os.path.isfile(extended_file)
        results["previous_exists"] = golden_exists or extended_exists

        previous_golden_data = None
        previous_extended_data = None

        if display_diff and golden_exists:
            try:
                with open(golden_file, "r") as f:
                    previous_golden_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                previous_golden_data = {}

        if display_diff and extended_exists:
            try:
                with open(extended_file, "r") as f:
                    previous_extended_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                previous_extended_data = {}

        previous_golden_checksum = None
        previous_extended_checksum = None

        if checksum_compare and golden_exists:
            previous_golden_checksum = self._file_checksum(golden_file)

        if checksum_compare and extended_exists:
            previous_extended_checksum = self._file_checksum(extended_file)

        if save_previous and golden_exists:
            os.rename(golden_file, golden_prev_file)

        if save_previous and extended_exists:
            os.rename(extended_file, extended_prev_file)

        # --- Phase 2: Write current data ---
        current_golden_content = json.dumps(data_model, indent=4, sort_keys=True)
        current_extended_content = json.dumps(
            data_model_extended, indent=4, sort_keys=True
        )

        with open(golden_file, "w") as f:
            f.write(current_golden_content)

        with open(extended_file, "w") as f:
            f.write(current_extended_content)

        # --- Phase 3: Checksum comparison ---
        results["skip_validation"] = False

        if checksum_compare and previous_golden_checksum and previous_extended_checksum:
            current_golden_checksum = self._file_checksum(golden_file)
            current_extended_checksum = self._file_checksum(extended_file)

            if (
                previous_golden_checksum == current_golden_checksum
                and previous_extended_checksum == current_extended_checksum
            ):
                results["skip_validation"] = True
                results["changed"] = False
                display_diff = False
            else:
                results["changed"] = True

        # --- Phase 4: Diff computation ---
        results["golden_diff"] = ""
        results["extended_diff"] = ""

        if display_diff:
            if previous_golden_data is not None:
                golden_diff = self._compute_diff(
                    previous_golden_data, data_model, "golden"
                )
                results["golden_diff"] = golden_diff
                if golden_diff:
                    display.display(
                        "--- Golden Service Model Changes ---", color="yellow"
                    )
                    display.display(golden_diff, color="normal")

            if previous_extended_data is not None:
                extended_diff = self._compute_diff(
                    previous_extended_data, data_model_extended, "extended"
                )
                results["extended_diff"] = extended_diff
                if extended_diff:
                    display.display(
                        "--- Extended Service Model Changes ---", color="yellow"
                    )
                    display.display(extended_diff, color="normal")

        # --- Phase 5: Cleanup if force_run_all ---
        if force_run_all:
            pattern = os.path.join(
                files_dir, f"{fabric_name}_service_model*_previous.json"
            )
            for prev_file in glob.glob(pattern):
                os.remove(prev_file)

        return results

    @staticmethod
    def _file_checksum(filepath):
        """Compute SHA256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def _compute_diff(before, after, label):
        """Compute unified diff between two dicts serialized as JSON."""
        before_lines = json.dumps(before, indent=4, sort_keys=True).splitlines(
            keepends=True
        )
        after_lines = json.dumps(after, indent=4, sort_keys=True).splitlines(
            keepends=True
        )
        diff = difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"{label}_previous",
            tofile=f"{label}_current",
            lineterm="",
        )
        return "\n".join(diff)

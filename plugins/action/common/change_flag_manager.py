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

from ansible.plugins.action import ActionBase
import json
import inspect
import os


class ChangeDetectionManager:
    """Manages change detection flags for fabric configurations."""

    def __init__(self, params):
        self.class_name = self.__class__.__name__
        method_name = inspect.stack()[0][3]

        self.fabric_type = params['fabric_type']
        self.fabric_name = params['fabric_name']
        self.role_path = params['role_path']
        self.file_path = f"{self.role_path}/files/{self.fabric_name}_changes_detected_flags.json"

    def initialize_flags(self):
        self.changes_detected_flags = {}
        self.changes_detected_flags[self.fabric_name] = {}
        self.changes_detected_flags[self.fabric_name][self.fabric_type] = {}

        # Supported Fabric Types VXLAN_EVPN, MSD, ISN, External, eBGP_VXLAN
        if self.fabric_type == "VXLAN_EVPN":
            self.changes_detected_flags[self.fabric_name][self.fabric_type] = {
                'changes_detected_fabric': False,
                'changes_detected_fabric_links': False,
                'changes_detected_edge_connections': False,
                'changes_detected_interface_dot1q': False,
                'changes_detected_interface_access_po': False,
                'changes_detected_interface_access': False,
                'changes_detected_interfaces': False,
                'changes_detected_interface_loopback': False,
                'changes_detected_interface_po_routed': False,
                'changes_detected_interface_routed': False,
                'changes_detected_interface_trunk_po': False,
                'changes_detected_interface_trunk': False,
                'changes_detected_interface_vpc': False,
                'changes_detected_interface_breakout': False,
                'changes_detected_interface_breakout_preprov': False,
                'changes_detected_inventory': False,
                'changes_detected_link_vpc_peering': False,
                'changes_detected_networks': False,
                'changes_detected_policy': False,
                'changes_detected_sub_interface_routed': False,
                'changes_detected_vpc_peering': False,
                'changes_detected_vpc_domain_id_resource': False,
                'changes_detected_vrfs': False,
                'changes_detected_underlay_ip_address': False,
                'changes_detected_any': False
            }
        if self.fabric_type == "ISN":
            self.changes_detected_flags[self.fabric_name][self.fabric_type] = {
                'changes_detected_fabric': False,
                # 'changes_detected_fabric_links': False,
                'changes_detected_edge_connections': False,
                'changes_detected_interface_dot1q': False,
                'changes_detected_interface_access_po': False,
                'changes_detected_interface_access': False,
                'changes_detected_interfaces': False,
                'changes_detected_interface_loopback': False,
                'changes_detected_interface_po_routed': False,
                'changes_detected_interface_routed': False,
                'changes_detected_interface_trunk_po': False,
                'changes_detected_interface_trunk': False,
                'changes_detected_interface_vpc': False,
                'changes_detected_interface_breakout': False,
                'changes_detected_interface_breakout_preprov': False,
                'changes_detected_inventory': False,
                'changes_detected_policy': False,
                'changes_detected_sub_interface_routed': False,
                'changes_detected_any': False
            }
        if self.fabric_type == "MSD":
            self.changes_detected_flags[self.fabric_name][self.fabric_type] = {
                'changes_detected_fabric': False,
                'changes_detected_bgw_anycast_vip': False,
                'changes_detected_vrfs': False,
                'changes_detected_networks': False,
                'changes_detected_any': False
            }
        if self.fabric_type == "External":
            self.changes_detected_flags[self.fabric_name][self.fabric_type] = {
                'changes_detected_inventory': False,
                'changes_detected_fabric': False,
                'changes_detected_edge_connections': False,
                'changes_detected_interface_dot1q': False,
                'changes_detected_interface_access_po': False,
                'changes_detected_interface_access': False,
                'changes_detected_interfaces': False,
                'changes_detected_interface_loopback': False,
                'changes_detected_interface_po_routed': False,
                'changes_detected_interface_routed': False,
                'changes_detected_interface_trunk_po': False,
                'changes_detected_interface_trunk': False,
                'changes_detected_interface_vpc': False,
                'changes_detected_interface_breakout': False,
                'changes_detected_interface_breakout_preprov': False,
                'changes_detected_sub_interface_routed': False,
                'changes_detected_vpc_peering': False,
                'changes_detected_policy': False,
                'changes_detected_any': False
            }
        if self.fabric_type == "eBGP_VXLAN":
            self.changes_detected_flags[self.fabric_name][self.fabric_type] = {
                'changes_detected_fabric': False,
                'changes_detected_fabric_links': False,
                'changes_detected_edge_connections': False,
                'changes_detected_interface_dot1q': False,
                'changes_detected_interface_access_po': False,
                'changes_detected_interface_access': False,
                'changes_detected_interfaces': False,
                'changes_detected_interface_loopback': False,
                'changes_detected_interface_po_routed': False,
                'changes_detected_interface_routed': False,
                'changes_detected_interface_trunk_po': False,
                'changes_detected_interface_trunk': False,
                'changes_detected_interface_vpc': False,
                'changes_detected_interface_breakout': False,
                'changes_detected_interface_breakout_preprov': False,
                'changes_detected_inventory': False,
                'changes_detected_link_vpc_peering': False,
                'changes_detected_networks': False,
                'changes_detected_policy': False,
                'changes_detected_sub_interface_routed': False,
                'changes_detected_vpc_peering': False,
                'changes_detected_vrfs': False,
                'changes_detected_any': False
            }

    def write_changes_detected_flags_to_file(self):
        """Write changes_detected_flags dictionary to file in JSON format"""

        # Remove file if it exists
        if os.path.exists(self.file_path):
            os.remove(self.file_path)

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        # Write dictionary to file in JSON format
        with open(self.file_path, 'w') as f:
            json.dump(self.changes_detected_flags, f, indent=2)

    def read_changes_detected_flags_from_file(self):
        """Read changes_detected_flags dictionary from JSON file"""

        if not os.path.exists(self.file_path):
            return {}

        with open(self.file_path, 'r') as f:
            return json.load(f)

    def update_change_detected_flag(self, flag_name, value):
        """Update a specific change detected flag and write back to file"""

        # Update the flag in the changes_detected_flags dictionary
        if self.fabric_name in self.changes_detected_flags:
            if self.fabric_type in self.changes_detected_flags[self.fabric_name]:
                if flag_name in self.changes_detected_flags[self.fabric_name][self.fabric_type]:
                    self.changes_detected_flags[self.fabric_name][self.fabric_type][flag_name] = value

                    # Write updated flags back to file
                    self.write_changes_detected_flags_to_file()
                    return True
                else:
                    print(f"Flag '{flag_name}' not found in fabric type '{self.fabric_type}' for fabric '{self.fabric_name}'")
                    return False
            else:
                print(f"Fabric type '{self.fabric_type}' not found in fabric '{self.fabric_name}'")
                return False
        else:
            print(f"Fabric name '{self.fabric_name}' not found in flags dictionary")
            return False

    def display_flag_values(self, task_vars):
        """Display current flag values in a nicely formatted table"""
        if not self.changes_detected_flags:
            print("No change detection flags found.")
            return

        # Display Execution Control Flags
        print("\n\n")
        print("-" * 40)
        print("Stage Execution Control Flags:")
        print("-" * 40)

        # Display run_map flag
        run_map = task_vars.get('force_run_all', 'Not Available')
        print(f"force_run_all  | {run_map}")

        # Display diff_run flag from run_map_read_result
        run_map_read_result = task_vars.get('run_map_read_result', {})
        diff_run = run_map_read_result.get('diff_run', 'Not Available') if isinstance(run_map_read_result, dict) else 'Not Available'
        print(f"diff_run       | {diff_run}")

        print("-" * 40)

        # Print header
        print("\n" + "=" * 80)
        print(f"Change Detection Flags for Fabric: {self.fabric_name}, Type: {self.fabric_type}")
        print("=" * 80)

        if self.fabric_name in self.changes_detected_flags:
            if self.fabric_type in self.changes_detected_flags[self.fabric_name]:
                flags = self.changes_detected_flags[self.fabric_name][self.fabric_type]

                # Calculate column widths
                max_flag_width = max(len(flag) for flag in flags.keys())
                flag_width = max(max_flag_width, 20)  # Minimum width of 20

                # Print table header
                print(f"{'Flag Name':<{flag_width}} | {'Status':<8}")
                print("-" * (flag_width + 11))

                # Sort flags for consistent display
                for flag_name in sorted(flags.keys()):
                    status = "TRUE" if flags[flag_name] else "FALSE"
                    status_color = status if not flags[flag_name] else f"**{status}**"
                    print(f"{flag_name:<{flag_width}} | {status_color:<8}")

                print("-" * (flag_width + 11))

                # Summary
                true_count = sum(1 for v in flags.values() if v)
                total_count = len(flags)
                print(f"Summary: {true_count}/{total_count} flags are TRUE")
            else:
                print(f"Fabric type '{self.fabric_type}' not found")
        else:
            print(f"Fabric '{self.fabric_name}' not found")

        print("=" * 80 + "\n")


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False
        results['flags'] = {}

        # Get data from Ansible task parameters
        params = {}
        params['fabric_type'] = self._task.args.get("fabric_type")
        params['fabric_name'] = self._task.args.get("fabric_name")
        params['role_path'] = self._task.args.get("role_path")
        params['operation'] = self._task.args.get("operation")
        params['change_flag'] = self._task.args.get("change_flag")
        params['flag_value'] = self._task.args.get("flag_value")

        for key in ['fabric_type', 'fabric_name', 'role_path', 'operation']:
            if params[key] is None:
                results['failed'] = True
                results['msg'] = f"Missing required parameter '{key}'"
                return results

        if params['operation'] not in ['initialize', 'update', 'get', 'display']:
            results['failed'] = True
            results['msg'] = "Parameter 'operation' must be one of: [initialize, update, get, display]"
            return results

        # Supported Operations (intialize, update)
        change_detection_manager = ChangeDetectionManager(params)

        if params['operation'] == "initialize":
            change_detection_manager.initialize_flags()
            change_detection_manager.write_changes_detected_flags_to_file()
            results['msg'] = f"Initialized change detection flags for fabric '{params['fabric_name']}' of type '{params['fabric_type']}'"

        if params['operation'] == "update":
            if params['change_flag'] is None:
                results['failed'] = True
                results['msg'] = "Missing required parameter 'change_flag' for update operation"
                return results

            if params['flag_value'] is None:
                results['failed'] = True
                results['msg'] = "Missing required parameter 'flag_value' for update operation"
                return results

            if not isinstance(params['flag_value'], bool):
                results['failed'] = True
                results['msg'] = "Parameter 'flag_value' must be a boolean (True or False)"
                return results

            change_detection_manager.changes_detected_flags = change_detection_manager.read_changes_detected_flags_from_file()
            success = change_detection_manager.update_change_detected_flag(params['change_flag'], params['flag_value'])

            # If any of the flags are updated to be true then also set the changes_detected_any flag to true
            if success and params['flag_value'] is True:
                success = change_detection_manager.update_change_detected_flag('changes_detected_any', True)
                self.process_write_result(success, 'changes_detected_any', True, params, results)

            self.process_write_result(success, params['change_flag'], params['flag_value'], params, results)

        if params['operation'] == "get":
            change_detection_manager.changes_detected_flags = change_detection_manager.read_changes_detected_flags_from_file()
            results['flags'] = change_detection_manager.changes_detected_flags[params['fabric_name']][params['fabric_type']]

        if params['operation'] == "display":
            change_detection_manager.changes_detected_flags = change_detection_manager.read_changes_detected_flags_from_file()
            change_detection_manager.display_flag_values(task_vars)
            from time import sleep
            sleep(2)

        return results

    def process_write_result(self, success, change_flag, change_value, params, results):
        if success:
            results['msg'] = f"Updated flag '{change_flag}' to '{change_value}' for fabric '{params['fabric_name']}' of type '{params['fabric_type']}'"
        else:
            results['failed'] = True
            results['msg'] = f"Failed to update flag '{change_flag}'"

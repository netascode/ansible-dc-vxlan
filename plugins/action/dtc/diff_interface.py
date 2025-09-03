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

import yaml
from ansible.utils.display import Display
from ansible.plugins.action import ActionBase
import logging

display = Display()

class ActionModule(ActionBase):
    """
    Action plugin to compare existing links with new links for a fabric.
    Identifies new/modified, removed, and unchanged items.
    """
    def run(self, tmp=None, task_vars=None):
        """
        Run the action plugin.
        """
        results = super(ActionModule, self).run(tmp, task_vars)
        results['interface_all'] = {}

        self.old_file_path = self._task.args['old_file']
        self.new_file_path = self._task.args['new_file']

        old_items = []
        new_items = []

        try:
            old_items = self.load_yaml(self.old_file_path)
        except (FileNotFoundError, IOError):
            display.warning(f"Old file not found: {self.old_file_path}, using empty list")

        try:
            new_items = self.load_yaml(self.new_file_path)
        except (FileNotFoundError, IOError):
            display.warning(f"New file not found: {self.new_file_path}, using empty list")

        updated_items, removed_items, equal_items = self.compare_items(old_items, new_items)

        display.v("New or Modified Items:\n%s", yaml.dump(updated_items, default_flow_style=False))
        display.v("---------------------------------")
        display.v("Remove Items:\n%s", yaml.dump(removed_items, default_flow_style=False))
        display.v("---------------------------------")
        display.v("Unchanged Items:\n%s", yaml.dump(equal_items, default_flow_style=False))

        from time import sleep ; sleep(10)

        results['interface_all'] = {"updated": updated_items, "removed": removed_items, "equal": equal_items}
        return results['interface_all']

    def load_yaml(self, filename):
        """
        Load YAML data from a file.
        """
        with open(filename, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or []

    def dict_key(self, item):
        """
        Return the unique key for an item (e.g., interface name).
        """
        if self.new_file_path.endswith('ndfc_interface_all.yml'):
            return item.get('name')
        elif self.new_file_path.endswith('ndfc_underlay_ip_address.yml'):
            return item.get('entity_name')
        elif self.new_file_path.endswith('ndfc_attach_vrfs.yml'):
            return item.get('vrf_name')
        else:
            return None

    def compare_items(self, old_items, new_items):
        """
        Compare old and new items, returning updated, removed, and equal items.
        """
        old_dict = {self.dict_key(item): item for item in old_items}
        new_dict = {self.dict_key(item): item for item in new_items}

        updated_items = [] # Updated items in new file
        removed_items = [] # Items removed in new file
        equal_items = []   # Items unchanged

        for key, new_item in new_dict.items():
            old_item = old_dict.get(key)
            if old_item is None:
                updated_items.append(new_item)
            elif old_item != new_item:
                updated_items.append(new_item)
            else:
                equal_items.append(new_item)

        for key, old_item in old_dict.items():
            if key not in new_dict:
                removed_items.append(old_item)

        return updated_items, removed_items, equal_items

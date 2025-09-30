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

import yaml
from ansible.utils.display import Display
from ansible.plugins.action import ActionBase

display = Display()


class ActionModule(ActionBase):
    """
    Action plugin to compare existing links with new links for a fabric.
    Identifies new/modified, removed, and unchanged items.
    """
    def __init__(self, *args, **kwargs):
        super(ActionModule, self).__init__(*args, **kwargs)
        self.old_file_path = None
        self.new_file_path = None

    def run(self, tmp=None, task_vars=None):
        """
        Run the action plugin.

        Args:
            tmp: Temporary directory for file operations
            task_vars: Variables available to the task

        Returns:
            dict: Results containing the comparison of items
        """
        if task_vars is None:
            task_vars = {}

        results = super(ActionModule, self).run(tmp, task_vars)
        results['compare'] = {}

        # Validate required arguments
        try:
            self.old_file_path = self._task.args.get('old_file')
            self.new_file_path = self._task.args.get('new_file')

            if not self.old_file_path or not self.new_file_path:
                raise ValueError("Both old_file and new_file arguments are required")

        except (AttributeError, KeyError) as e:
            return {'failed': True, 'msg': f'Missing required argument: {str(e)}'}

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

        if self.new_file_path.endswith('ndfc_interface_all.yml'):
            removed_items = self.order_interface_remove(removed_items)

        display.v("New or Modified Items:\n%s", yaml.dump(updated_items, default_flow_style=False))
        display.v("---------------------------------")
        display.v("Remove Items:\n%s", yaml.dump(removed_items, default_flow_style=False))
        display.v("---------------------------------")
        display.v("Unchanged Items:\n%s", yaml.dump(equal_items, default_flow_style=False))

        results['compare'] = {"updated": updated_items, "removed": removed_items, "equal": equal_items}
        return results['compare']

    def load_yaml(self, filename):
        """
        Load YAML data from a file.
        """
        with open(filename, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or []

    KEY_MAPPING = {
        'ndfc_underlay_ip_address.yml': 'entity_name',
        'ndfc_attach_vrfs.yml': 'vrf_name',
        'ndfc_attach_networks.yml': 'net_name',
        'ndfc_vpc_domain_id_resource.yml': 'entity_name',
        'ndfc_vpc_peering.yml': 'peerOneId'
    }

    def _create_fabric_link_key(self, item):
        """
        Create a unique key for fabric links from multiple attributes.

        Args:
            item (dict): The fabric link item containing link details

        Returns:
            str: A unique key for the fabric link or None if required fields are missing
        """
        required_fields = ['dst_fabric', 'src_device', 'src_interface', 'dst_interface']
        if not all(item.get(field) for field in required_fields):
            return None

        return '_'.join([item.get(field) for field in required_fields])

    def _create_interface_key(self, item):
        """
        Create a unique key for interfaces from multiple attributes.

        Args:
            item (dict): The interface item containing interface details

        Returns:
            str: A unique key for the interface per switch or None if required fields are missing
        """
        required_fields = ['name', 'switch']
        if not all(item.get(field) for field in required_fields):
            return None

        switch_value = item.get('switch')
        # Handle both string and list types for switch field
        if isinstance(switch_value, list):
            if not switch_value:  # Empty list check
                return None
            switch_id = switch_value[0]
        else:
            switch_id = switch_value

        return f"{item.get('name')}_{switch_id}"

    def dict_key(self, item):
        """
        Return the unique key for an item based on its type.

        Args:
            item (dict): The item to generate a key for

        Returns:
            str: The unique key for the item, or None if no key could be generated
        """
        if not isinstance(item, dict):
            return None

        filename = self.new_file_path

        # Special handling for fabric links due to composite key
        if filename.endswith('ndfc_fabric_links.yml'):
            return self._create_fabric_link_key(item)

        # Special handling for interfaces due to composite key
        if filename.endswith('ndfc_interface_all.yml'):
            return self._create_interface_key(item)

        # Find matching file type and return corresponding key
        for file_type, key_attr in self.KEY_MAPPING.items():
            if filename.endswith(file_type):
                return item.get(key_attr)

        return None

    def compare_items(self, old_items, new_items):
        """
        Compare old and new items, returning updated, removed, and equal items.
        """

        old_dict = {self.dict_key(item): item for item in old_items}
        new_dict = {self.dict_key(item): item for item in new_items}

        updated_items = []  # Updated items in new file
        removed_items = []  # Items removed in new file
        equal_items = []  # Items unchanged

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

    def order_interface_remove(self, removed_items):
        """
        Order interface removals to avoid dependency issues.
        Ensures that port-channels are removed after their member interfaces.

        Args:
            removed_items (list): List of interface items to be removed

        Returns:
            list: Ordered list of interface items for removal (port-channels first,
                  then ethernet interfaces, then other interface types)

        Note:
            This ordering helps prevent dependency conflicts during interface removal.
            Port-channels should be removed before their member ethernet interfaces
            to avoid configuration errors.
        """
        # The order in which interfaces are configured matters during removal.
        # Configuration Order:
        #  - Breakout Interfaces        (Type: breakout)
        #  - Trunk Interfaces           (Type: eth)
        #  - Access Interfaces          (Type: eth)
        #  - Access Port-Channels       (Type: pc)
        #  - Trunk Port-Channels        (Type: pc)
        #  - Routed Interfaces          (Type: eth)
        #  - Routed Sub-Interfaces      (Type: sub_int)
        #  - Routed Port-Channels       (Type: pc)
        #  - Loopback Interfaces        (Type: lo)
        #  - Dot1Q Sub-Interfaces       (Type: eth)
        #  - vPC Interfaces             (Type: vpc)

        # Remove in the reverse order to avoid dependency issues
        vpc_interfaces = [item for item in removed_items if item.get('type') == 'vpc']
        loopback_interfaces = [item for item in removed_items if item.get('type') == 'lo']
        port_channels = [item for item in removed_items if item.get('type') == 'pc']
        routed_sub_interfaces = [item for item in removed_items if item.get('type') == 'sub_int']
        ethernet_interfaces = [item for item in removed_items if item.get('type') == 'eth']
        breakout_interfaces = [item for item in removed_items if item.get('type') == 'breakout']

        # Return ordered list: port-channels first, then ethernet interfaces, then others
        all_interfaces = vpc_interfaces + loopback_interfaces + port_channels + routed_sub_interfaces + ethernet_interfaces + breakout_interfaces
        return all_interfaces
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

# This is an example file for help functions that can be called by
# our various action plugins for common routines.
#
# For example in prepare_serice_model.py we can do the following:
#  from ..helper_functions import do_something

def data_model_key_check(tested_object, keys):
    """
    Check if key(s) are found and exist in the data model.

    :Parameters:
        :tested_object (dict): Data model to check for keys.
        :keys (list): List of keys to check in the data model.

    :Returns:
        :dm_key_dict (dict): Dictionary of lists for keys found, not found, and corresponding data or empty data.

    :Raises:
        N/A
    """
    dm_key_dict = {'keys_found': [], 'keys_not_found': [], 'keys_data': [], 'keys_no_data': []}
    for key in keys:
        if tested_object and key in tested_object:
            dm_key_dict['keys_found'].append(key)
            tested_object = tested_object[key]
            if tested_object:
                dm_key_dict['keys_data'].append(key)
            else:
                dm_key_dict['keys_no_data'].append(key)
        else:
            dm_key_dict['keys_not_found'].append(key)

    return dm_key_dict


def hostname_to_ip_mapping(data_model):
    """
    Update in-memory data model with IP address mapping to hostname.

    :Parameters:
        :data_model (dict): The in-memory data model.

    :Returns:
        :data_model: The updated in-memory data model with IP address mapping to hostname.

    :Raises:
        N/A
    """
    topology_switches = data_model['vxlan']['topology']['switches']
    for switch in data_model['vxlan']['policy']['switches']:
        if any(sw['name'] == switch['name'] for sw in topology_switches):
            found_switch = next((item for item in topology_switches if item["name"] == switch['name']))
            if found_switch.get('management').get('management_ipv4_address'):
                switch['mgmt_ip_address'] = found_switch['management']['management_ipv4_address']
            elif found_switch.get('management').get('management_ipv6_address'):
                switch['mgmt_ip_address'] = found_switch['management']['management_ipv6_address']

    return data_model


def ndfc_get_switch_policy(self, task_vars, tmp, switch_serial_number):
    """
    Get NDFC policy for a given managed switch by the switch's serial number.

    :Parameters:
        :self: Ansible action plugin instance object.
        :task_vars (dict): Ansible task vars.
        :tmp (None, optional): Ansible tmp object. Defaults to None via Action Plugin.
        :switch_serial_number (str): The serial number of the managed switch for which the NDFC policy is to be retrieved.

    :Returns:
        :policy_data: The NDFC policy data for the given switch.

    :Raises:
        N/A
    """
    policy_data = self._execute_module(
        module_name="cisco.dcnm.dcnm_rest",
        module_args={
            "method": "GET",
            "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/policies/switches/{switch_serial_number}/SWITCH/SWITCH"
        },
        task_vars=task_vars,
        tmp=tmp
    )

    return policy_data


def ndfc_get_switch_policy_using_template(self, task_vars, tmp, switch_serial_number, template_name):
    """
    Get NDFC policy for a given managed switch by the switch's serial number and a specified NDFC template name.

    :Parameters:
        :self: Ansible action plugin instance object.
        :task_vars (dict): Ansible task vars.
        :tmp (None, optional): Ansible tmp object. Defaults to None via Action Plugin.
        :switch_serial_number (str): The serial number of the managed switch for which the NDFC policy is to be retrieved.
        :template_name (str): The name of the NDFC template for which the policy is to be retrieved.

    :Returns:
        :policy_match: The NDFC policy data for the given switch and matching template.

    :Raises:
        :Exception: If the policy for the given switch and template is not found.
    """
    policy_data = ndfc_get_switch_policy(self, task_vars, tmp, switch_serial_number)

    try:
        policy_match = next(
            (item for item in policy_data["response"]["DATA"] if item["templateName"] == template_name and item['serialNumber'] == switch_serial_number)
        )
    except StopIteration:
        if template_name == "host_11_1":
            policy_match = None
        else:
            err_msg = f"Policy for template {template_name} and switch {switch_serial_number} not found!"
            err_msg += f" Please ensure switch with serial number {switch_serial_number} is part of the fabric."
            raise Exception(err_msg)

    return policy_match


def ndfc_get_switch_policy_using_desc(self, task_vars, tmp, switch_serial_number, prefix):
    """
    Get NDFC policy for a given managed switch by the switch's serial number and the prepanded string nac.

    :Parameters:
        :self: Ansible action plugin instance object.
        :task_vars (dict): Ansible task vars.
        :tmp (None, optional): Ansible tmp object. Defaults to None via Action Plugin.
        :switch_serial_number (str): The serial number of the managed switch for which the NDFC policy is to be retrieved.

    :Returns:
        :policy_match: The NDFC policy data for the given switch and matching template.

    :Raises:
        N/A
    """
    policy_data = ndfc_get_switch_policy(self, task_vars, tmp, switch_serial_number)

    policy_match = [
        item for item in policy_data["response"]["DATA"]
        if item.get("description", None) and item.get("description", None).startswith(prefix) and item["source"] == ""
    ]

    return policy_match


def ndfc_get_fabric_attributes(self, task_vars, tmp, fabric):
    """
    Get NDFC fabric attributes.

    :Parameters:
        :self: Ansible action plugin instance object.
        :task_vars (dict): Ansible task vars.
        :tmp (None, optional): Ansible tmp object. Defaults to None via Action Plugin.
        :fabric (str): The fabric name to be retrieved.

    :Returns:
        :fabric_attributes: The NDFC fabric attributes data for the given fabric.

    :Raises:
        N/A
    """
    fabric_response = self._execute_module(
        module_name="cisco.dcnm.dcnm_rest",
        module_args={
            "method": "GET",
            "path": f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/{fabric}",
        },
        task_vars=task_vars,
        tmp=tmp
    )

    fabric_attributes = fabric_response['response']['DATA']['nvPairs']

    return fabric_attributes


def ndfc_get_fabric_switches(self, task_vars, tmp, fabric):
    """
    Get NDFC fabric switches.

    :Parameters:
        :self: Ansible action plugin instance object.
        :task_vars (dict): Ansible task vars.
        :tmp (None, optional): Ansible tmp object. Defaults to None via Action Plugin.
        :fabric (str): The fabric name to be retrieved.

    :Returns:
        :fabric_switches: The NDFC fabric switches data for the given fabric.

    :Raises:
        N/A
    """
    fabric_response = self._execute_module(
        module_name="cisco.dcnm.dcnm_inventory",
        module_args={
            "fabric": fabric,
            "state": "query"
        },
        task_vars=task_vars,
        tmp=tmp
    )

    fabric_switches = []
    for fabric_switch in fabric_response['response']:
        if 'logicalName' in fabric_switch:
            fabric_switches.append(
                {
                    'hostname': fabric_switch['logicalName'],
                    'name': fabric_switch['logicalName'],
                    'mgmt_ip_address': fabric_switch['ipAddress'],
                    'fabric_name': fabric_switch['fabricName'],
                    'serial_number': fabric_switch['serialNumber'],
                    'role': fabric_switch['switchRole'],
                }
            )

    return fabric_switches


def restructure_leaf_tor_data(switches_list, topology_switches, tor_peers):
    """Transform a flat switches list into the nested structure with TOR
    entries under their parent leaf switches.

    Each TOR is placed under ALL of its parent leaves that are present in the
    attach group. If a parent leaf is not explicitly listed in the attach group,
    a synthetic leaf entry is created automatically from topology data.

    Args:
        switches_list: List of switch dicts from network_attach_group
        topology_switches: List of switch dicts from vxlan.topology.switches
        tor_peers: List of tor_peers dicts from vxlan.topology.tor_peers

    Returns:
        Restructured switches list with TOR entries nested under parent leaves
    """
    # Build set of TOR hostnames from topology
    tor_hostnames = {
        sw['name'] for sw in topology_switches if sw.get("role") == "tor"
    }

    # Build TOR -> parent leaves mapping from tor_peers
    # Each TOR maps to a list of its parent leaf hostnames
    tor_to_parents = {}
    for peer in tor_peers:
        parent_leaves = []
        if peer.get("parent_leaf1"):
            parent_leaves.append(peer['parent_leaf1'])
        if peer.get("parent_leaf2"):
            parent_leaves.append(peer['parent_leaf2'])

        for key in ("tor1", "tor2"):
            tor_name = peer.get(key)
            if tor_name:
                tor_to_parents[tor_name] = parent_leaves

    # # Build topology hostname -> switch data mapping for creating synthetic entries
    # topology_by_name = {sw['name']: sw for sw in topology_switches}

    # Separate leaf entries and TOR entries
    leaf_entries = []
    tor_entries = []

    for sw in switches_list:
        hostname = sw.get("hostname", "")
        if hostname in tor_hostnames:
            tor_entries.append(sw)
        else:
            leaf_entries.append(sw)

    # Initialize empty 'tors' list for each leaf entry
    for leaf in leaf_entries:
        if "tors" not in leaf:
            leaf['tors'] = []

    # Build hostname -> leaf entry mapping for quick lookup
    leaf_by_hostname = {leaf['hostname']: leaf for leaf in leaf_entries}

    # Collect all required parent leaf hostnames from TOR entries
    # and create synthetic leaf entries for any that are not in the attach group
    for tor_entry in tor_entries:
        tor_hostname = tor_entry['hostname']
        parent_leaves = tor_to_parents.get(tor_hostname, [])
        for parent_hostname in parent_leaves:
            if parent_hostname not in leaf_by_hostname:
                # Create a synthetic leaf entry from topology data
                synthetic_leaf = {'hostname': parent_hostname, 'tors': []}
                leaf_entries.append(synthetic_leaf)
                leaf_by_hostname[parent_hostname] = synthetic_leaf

    # Assign each TOR to ALL of its parent leaves present in this attach group
    for tor_entry in tor_entries:
        tor_hostname = tor_entry['hostname']
        parent_leaves = tor_to_parents.get(tor_hostname, [])
        valid_parents = [p for p in parent_leaves if p in leaf_by_hostname]

        if valid_parents:
            for parent_hostname in valid_parents:
                leaf_by_hostname[parent_hostname]['tors'].append(tor_entry)
        else:
            # No parent leaf defined in tor_peers - keep TOR as top-level entry
            leaf_entries.append(tor_entry)

    return leaf_entries

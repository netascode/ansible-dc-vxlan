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

"""
Remove Resources — Consolidated removal pipeline for all fabric types.

Replaces the dtc/remove role's per-fabric-type sub_main_*.yml files and
task files (~16 files, ~800 lines YAML) with a single data-driven plugin.

Pipeline definitions are loaded from resources/remove_resources.yml.

Extends PipelineRunnerBase with remove-specific behavior:
  - Recommendation #2: delete_mode_guard safety flags per step
  - Recommendation #4: Correct vPC peers module (dcnm_vpc_pair with src_fabric)
  - state_full_run: Dual-state removal (deleted for diff_run, overridden for full)
  - skip_if_child_fabric: Guard for VRFs/networks on active MSD child fabrics

Shared infrastructure (module execution, pipeline skeleton, tag filtering,
change flag guards, multisite methods) lives in plugin_utils/.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.utils.display import Display

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.pipeline_base import (
    PipelineRunnerBase,
)
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.dtc_action_base import (
    DtcPipelineActionBase,
)

display = Display()


class ResourceRemover(PipelineRunnerBase):
    """
    Remove pipeline runner.

    Extends PipelineRunnerBase with remove-specific data resolution
    (diff.removed with dual-state), additional guards (delete_mode,
    child_fabric), and controller query helpers.
    """

    REGISTRY_KEY = 'remove_resources'
    OPERATION = 'remove'

    def __init__(self, params, executor, task_vars):
        super().__init__(params, executor, task_vars)
        self.stage_remove = params.get('stage_remove', False)

        # Recommendation #2: delete_mode_guard support
        # Read delete mode flags from task_vars (user-configurable via group_vars/host_vars)
        self.delete_modes = {
            'interface_delete_mode': task_vars.get('interface_delete_mode', False),
            'vrf_delete_mode': task_vars.get('vrf_delete_mode', False),
            'network_delete_mode': task_vars.get('network_delete_mode', False),
            'vpc_delete_mode': task_vars.get('vpc_delete_mode', False),
            'inventory_delete_mode': task_vars.get('inventory_delete_mode', False),
            'edge_connections_delete_mode': task_vars.get('edge_connections_delete_mode', False),
            'policy_delete_mode': task_vars.get('policy_delete_mode', False),
            'tor_pairing_delete_mode': task_vars.get('tor_pairing_delete_mode', False),
            'link_fabric_delete_mode': task_vars.get('link_fabric_delete_mode', False),
            'link_vpc_delete_mode': task_vars.get('link_vpc_delete_mode', False),
        }

    # ══════════════════════════════════════════════════════════════════════════
    # Pipeline Hooks (remove-specific overrides)
    # ══════════════════════════════════════════════════════════════════════════

    def _pre_pipeline_setup(self):
        """Pre-fetch fabric switch list for guards and internal methods."""
        self.fabric_switch_list = self._get_fabric_switches()
        return {'switch_list': self.fabric_switch_list}

    def _check_additional_guards(self, step, context):
        """
        Remove-specific guards: delete_mode, child_fabric.

        Checked before the shared change_flag_guard in the base class.
        """
        resource_name = step['resource_name']
        module = step['module']

        # ── Guard 1: delete_mode_guard (Recommendation #2) ────────────
        if not self._check_delete_mode(step):
            display.v(
                f"REMOVE [{self.fabric_name}] Skipping {resource_name}: "
                f"delete_mode_guard '{step.get('delete_mode_guard')}' is disabled"
            )
            return {
                'resource_name': resource_name,
                'module': module,
                'status': 'skipped',
                'reason': (
                    f"delete_mode_guard '{step.get('delete_mode_guard')}' "
                    f"is disabled"
                ),
            }

        # ── Guard 2: skip_if_child_fabric ─────────────────────────────
        if step.get('skip_if_child_fabric') and self._is_active_child_fabric():
            display.v(
                f"REMOVE [{self.fabric_name}] Skipping {resource_name}: "
                f"fabric is an active MSD child"
            )
            return {
                'resource_name': resource_name,
                'module': module,
                'status': 'skipped',
                'reason': 'active child fabric — skipping to prevent MSD conflict',
            }

        return None  # All guards passed

    # ══════════════════════════════════════════════════════════════════════════
    # Data Resolution (remove-specific)
    # ══════════════════════════════════════════════════════════════════════════

    def _resolve_step_data(self, resource_name, step):
        """
        Determine the data set and module state for resource removal.

        When diff_run is active and force_run_all is False:
          - Uses diff.removed list with the default 'state' (typically 'deleted')
        When diff_run is disabled or force_run_all is True:
          - If full_run_strategy is 'controller_diff': queries NDFC for live
            state, diffs against the data model, and returns only items on the
            controller that are NOT in the data model, with state 'deleted'.
          - If full_run_strategy is 'overridden': sends full resource data
            with state 'overridden' for full reconciliation against NDFC.
          - Otherwise uses full resource data with 'state_full_run' if declared
            (typically 'overridden'), falling back to 'state'.

        Args:
            resource_name: Logical name of the resource.
            step: Pipeline step dict from remove_resources.yml.

        Returns:
            Tuple of (data_list, resolved_state_string).
        """
        resource_entry = self.resource_data.get(resource_name, {})
        default_state = step.get('state')
        full_run_state = step.get('state_full_run')
        data_key_full_run = step.get('data_key_full_run', 'data')
        full_run_override_key = step.get('data_key_overridden')

        if not isinstance(resource_entry, dict):
            return (resource_entry if resource_entry else [], default_state)

        # Some remove steps are intentionally always full-reconciliation and
        # never diff-narrowed (for example switch inventory removal, which
        # always uses state=overridden in the original role).
        if default_state == 'overridden':
            data_key = full_run_override_key or data_key_full_run
            if data_key == 'data' and 'module_data' in resource_entry:
                data_key = 'module_data'
            data = resource_entry.get(data_key, [])
            return (data, default_state)

        # Diff-based run: use diff.removed with default state (deleted)
        if self.run_map_diff_run and not self.force_run_all:
            diff = resource_entry.get('diff')
            if diff and isinstance(diff, dict):
                removed = diff.get('removed', [])
                if removed:
                    return (removed, default_state)
            return ([], default_state)

        # Full run with controller_diff strategy: query NDFC, diff, return
        # only items on the controller that are absent from the data model.
        full_run_strategy = step.get('full_run_strategy')

        if full_run_strategy == 'controller_diff':
            method_name = f"_controller_diff_{resource_name}"
            method = getattr(self, method_name, None)
            if method is None:
                display.warning(
                    f"REMOVE [{self.fabric_name}] No controller diff method "
                    f"'{method_name}' found for {resource_name} — skipping"
                )
                return ([], default_state)
            data = resource_entry.get('data', [])
            items_to_delete = method(data)
            return (items_to_delete, default_state)

        # Full run with overridden strategy: send full data with state overridden
        # for full reconciliation against the controller.
        if full_run_strategy == 'overridden':
            data_key = (
                full_run_override_key
                or step.get('data_key_full_run')
                or ('data_remove_overridden' if 'data_remove_overridden' in resource_entry else None)
                or ('module_data' if 'module_data' in resource_entry else 'data')
            )
            data = resource_entry.get(data_key, [])
            return (data, 'overridden')

        # Full run (legacy): use full data with full_run_state if declared
        resolved_state = full_run_state if full_run_state else default_state
        if data_key_full_run == 'data' and 'module_data' in resource_entry:
            data_key_full_run = 'module_data'
        data = resource_entry.get(data_key_full_run, [])
        return (data, resolved_state)

    # ══════════════════════════════════════════════════════════════════════════
    # Remove-Specific Guard Helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _check_delete_mode(self, step):
        """
        Check if the user-configurable delete mode flag allows this step.

        Recommendation #2: Each pipeline step can declare a delete_mode_guard
        field. If present, the corresponding user variable must be truthy
        for the step to execute. If absent, the step always executes.

        Args:
            step: Pipeline step dict.

        Returns:
            True if the step should execute, False if it should be skipped.
        """
        delete_mode_flag = step.get('delete_mode_guard')
        if not delete_mode_flag:
            return True  # No guard configured — always execute
        return bool(self.delete_modes.get(delete_mode_flag, False))

    def _is_active_child_fabric(self):
        """
        Check if the current fabric is an active child in an MSD deployment.

        Caches the result as an instance variable after the first API call,
        since multiple pipeline steps may check this within a single execution.

        Returns:
            True if the fabric is an active MSD child, False otherwise.
        """
        if hasattr(self, '_cached_child_fabric_result'):
            return self._cached_child_fabric_result

        # If centralized controller discovery has already set this fact,
        # use it directly from task_vars
        if 'is_active_child_fabric' in self.task_vars:
            self._cached_child_fabric_result = bool(
                self.task_vars['is_active_child_fabric']
            )
            return self._cached_child_fabric_result

        # Fall back to querying the controller
        result = self.executor.execute_rest(
            "GET",
            "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control"
            "/fabrics/msd/fabric-associations",
        )

        is_child = False
        try:
            associations = result.get('response', {}).get('DATA', [])
            if isinstance(associations, list):
                for assoc in associations:
                    if (assoc.get('fabricName') == self.fabric_name and
                            assoc.get('fabricParent', 'None') != 'None'):
                        is_child = True
                        break
        except (KeyError, TypeError, IndexError):
            pass

        self._cached_child_fabric_result = is_child
        return is_child

    def _get_fabric_switches(self):
        """
        Get the list of switches in the current fabric from NDFC.

        If centralized controller discovery has set the fabric_switches fact,
        uses that directly. Otherwise queries the controller.

        Returns:
            List of switch dicts, or empty list if no switches.
        """
        # Use centralized fact if available (Recommendation #3)
        if 'fabric_switches' in self.task_vars:
            switches = self.task_vars['fabric_switches']
            return switches if isinstance(switches, list) else []

        # Fall back to querying the controller
        result = self.executor.execute_rest(
            "GET",
            f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control"
            f"/fabrics/{self.fabric_name}/inventory/switchesByFabric",
        )

        try:
            data = result.get('response', {}).get('DATA', [])
            return data if isinstance(data, list) else []
        except (KeyError, TypeError):
            return []

    # ══════════════════════════════════════════════════════════════════════════
    # Remove-Specific Internal Methods
    # ══════════════════════════════════════════════════════════════════════════

    def _fabric_links_query_and_remove(self, resource_name, step):
        """
        Query NDFC for existing fabric links and identify unmanaged links for removal.

        Replicates the pre-processing from roles/dtc/remove/tasks/common/links.yml:
          1. Query existing links from NDFC (dcnm_links state: query)
          2. Run links_filter_and_remove action plugin to identify unmanaged links
          3. Update self.resource_data['fabric_links'] with links to remove

        The subsequent dcnm_links step picks up the filtered data via
        _resolve_step_data naturally.
        """
        # Step 1: Query existing links from NDFC
        query_result = self.executor.execute(
            module_name="cisco.dcnm.dcnm_links",
            state="query",
            config=[{"dst_fabric": self.fabric_name}],
            fabric_name=self.fabric_name,
            fabric_param="src_fabric",
        )

        existing_links = query_result.get('response', [])
        if not existing_links:
            # No existing links — nothing to remove
            resource_entry = self.resource_data.get('fabric_links', {})
            if isinstance(resource_entry, dict):
                resource_entry['module_data'] = []
            else:
                self.resource_data['fabric_links'] = {'module_data': []}
            return {'changed': False, 'msg': 'No existing links on controller'}

        # Step 2: Get the full configured fabric_links data (not diff-narrowed)
        resource_entry = self.resource_data.get('fabric_links', {})
        if isinstance(resource_entry, dict):
            fabric_links_data = resource_entry.get('data', [])
        else:
            fabric_links_data = resource_entry if resource_entry else []

        switches = (
            self.data_model.get('vxlan', {})
            .get('topology', {})
            .get('switches', [])
        )

        # Step 3: Filter via links_filter_and_remove action plugin
        filter_result = self.executor.execute_plugin(
            module_name="cisco.nac_dc_vxlan.dtc.links_filter_and_remove",
            module_args={
                "existing_links": existing_links,
                "fabric_links": fabric_links_data,
                "switch_data_model": switches,
            },
        )

        if filter_result.get('failed'):
            return {
                'failed': True,
                'msg': (
                    f"links_filter_and_remove failed: "
                    f"{filter_result.get('msg', 'unknown error')}"
                ),
            }

        # Step 4: Update resource_data so the next step picks up links to remove
        links_to_remove = filter_result.get('links_to_be_removed', [])

        resource_entry = self.resource_data.get('fabric_links', {})
        if isinstance(resource_entry, dict):
            resource_entry['module_data'] = links_to_remove
        else:
            self.resource_data['fabric_links'] = {'module_data': links_to_remove}

        display.v(
            f"REMOVE [{self.fabric_name}] fabric_links: "
            f"{len(existing_links)} on controller → {len(links_to_remove)} to remove"
        )

        return {'changed': False}

    # ══════════════════════════════════════════════════════════════════════════
    # Controller Diff — Query NDFC, diff against data model, return deletions
    # ══════════════════════════════════════════════════════════════════════════

    def _get_fabric_id(self):
        """
        Get the numeric fabric ID from NDFC for the current fabric.

        Caches the result on the instance after the first API call.

        Returns:
            Integer fabric ID, or None if the query fails.
        """
        if hasattr(self, '_cached_fabric_id'):
            return self._cached_fabric_id

        result = self.executor.execute_rest(
            "GET",
            f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control"
            f"/fabrics/{self.fabric_name}",
        )

        fabric_id = None
        try:
            response = result.get('response', {})
            data = response.get('DATA', response)
            if isinstance(data, str):
                import json
                data = json.loads(data)
            fabric_id = data.get('id')
        except (KeyError, TypeError, ValueError):
            pass

        self._cached_fabric_id = fabric_id
        return fabric_id

    def _build_switch_serial_map(self):
        """
        Build a mapping of switch serial numbers to management IP addresses.

        Uses the switch list already fetched in _pre_pipeline_setup().
        Caches the result on the instance.

        Returns:
            Dict mapping serialNumber → ipAddress (management IP).
        """
        if hasattr(self, '_cached_serial_to_ip'):
            return self._cached_serial_to_ip

        serial_to_ip = {}
        for switch in self.fabric_switch_list:
            serial = switch.get('serialNumber')
            ip = switch.get('ipAddress')
            if serial and ip:
                serial_to_ip[serial] = ip

        self._cached_serial_to_ip = serial_to_ip
        return serial_to_ip

    # ── Interface type mapping ────────────────────────────────────────────
    # Map NDFC underlayPoliciesStr template names to dcnm_interface types.
    # Interfaces without a recognized template are skipped (discovered-only).
    NDFC_POLICY_TO_INTERFACE_TYPE = {
        'int_trunk_host': 'eth',
        'int_routed_host': 'eth',
        'int_access_host': 'eth',
        'int_dot1q': 'sub_int',
        'int_routed_host_sub': 'sub_int',
        'int_port_channel_trunk_host': 'pc',
        'int_port_channel_access_host': 'pc',
        'int_port_channel_routed_host': 'pc',
        'int_vpc_trunk_host': 'vpc',
        'int_vpc_access_host': 'vpc',
        'int_loopback': 'lo',
        'int_fabric_loopback_11_1': 'lo',
        'int_pre_provision_intra_fabric_link': 'eth',
        'int_intra_fabric_num_link': 'eth',
        'int_intra_fabric_unnum_link': 'eth',
    }

    # Map NDFC ifType values to dcnm_interface types as a fallback.
    NDFC_IFTYPE_TO_INTERFACE_TYPE = {
        'INTERFACE_ETHERNET': 'eth',
        'INTERFACE_PORT_CHANNEL': 'pc',
        'INTERFACE_VPC': 'vpc',
        'INTERFACE_LOOPBACK': 'lo',
        'INTERFACE_VLAN': 'eth',
        'SUBINTERFACE': 'sub_int',
    }

    def _controller_diff_interface_all(self, data_model_list):
        """
        Query NDFC for all managed interfaces and return those not in the data model.

        Strategy:
          1. Get fabric ID → query globalInterface API
          2. Filter to policy-managed interfaces only
          3. Build sets keyed on (interface_name, switch_ip) for O(n) diffing
          4. Return items on controller but absent from data model

        Args:
            data_model_list: List of interface dicts from the rendered data model.

        Returns:
            List of interface dicts formatted for dcnm_interface state: deleted.
        """
        fabric_id = self._get_fabric_id()
        if fabric_id is None:
            display.warning(
                f"REMOVE [{self.fabric_name}] Could not retrieve fabric ID "
                f"— skipping controller diff for interfaces"
            )
            return []

        result = self.executor.execute_rest(
            "GET",
            f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest"
            f"/globalInterface?navId={fabric_id}",
        )

        controller_interfaces = []
        try:
            response = result.get('response', {})
            data = response.get('DATA', response)
            if isinstance(data, str):
                import json
                data = json.loads(data)
            if isinstance(data, list):
                controller_interfaces = data
        except (KeyError, TypeError, ValueError):
            display.warning(
                f"REMOVE [{self.fabric_name}] Failed to parse globalInterface "
                f"response — skipping controller diff for interfaces"
            )
            return []

        serial_to_ip = self._build_switch_serial_map()

        # Build data model set: (interface_name, switch_ip)
        dm_keys = set()
        for iface in data_model_list:
            name = iface.get('name', '')
            switches = iface.get('switch', [])
            if isinstance(switches, list):
                for sw_ip in switches:
                    dm_keys.add((name, sw_ip))
            elif isinstance(switches, str):
                dm_keys.add((name, switches))

        # Filter controller interfaces to policy-managed only and diff
        items_to_delete = []
        for ctrl_iface in controller_interfaces:
            # Skip interfaces without NDFC-managed policies
            underlay_policies = ctrl_iface.get('underlayPolicies')
            overlay_str = ctrl_iface.get('overlayPoliciesStr', 'NA')
            if not underlay_policies and overlay_str == 'NA':
                continue

            # Skip mgmt interfaces — never managed by the data model
            if_type = ctrl_iface.get('ifType', '')
            if if_type == 'INTERFACE_MGMT':
                continue

            # Skip discovered-only interfaces not managed through policies
            if ctrl_iface.get('discovered') and not ctrl_iface.get('policyName'):
                underlay_str = ctrl_iface.get('underlayPoliciesStr', '')
                if not underlay_str or underlay_str == 'int_mgmt':
                    continue

            if_name = ctrl_iface.get('ifName', '')
            serial_no = ctrl_iface.get('serialNo', '')
            switch_ip = serial_to_ip.get(serial_no, '')

            if not switch_ip:
                continue

            ctrl_key = (if_name, switch_ip)
            if ctrl_key not in dm_keys:
                # Resolve interface type from policy template or ifType
                iface_type = None
                if underlay_policies and isinstance(underlay_policies, list):
                    template = underlay_policies[0].get('templateName', '')
                    iface_type = self.NDFC_POLICY_TO_INTERFACE_TYPE.get(template)
                if not iface_type:
                    iface_type = self.NDFC_IFTYPE_TO_INTERFACE_TYPE.get(if_type)
                if not iface_type:
                    continue  # Unknown type — skip

                items_to_delete.append({
                    'name': if_name,
                    'type': iface_type,
                    'switch': [switch_ip],
                    'deploy': False,
                })

        display.v(
            f"REMOVE [{self.fabric_name}] Controller diff for interfaces: "
            f"{len(controller_interfaces)} on controller, "
            f"{len(dm_keys)} in data model, "
            f"{len(items_to_delete)} to delete"
        )

        return items_to_delete

    def _controller_diff_vrfs(self, data_model_list):
        """
        Query NDFC for all VRFs and return those not in the data model.

        Strategy:
          1. Query top-down VRF API for current fabric
          2. Build set of VRF names from data model
          3. Return controller VRFs absent from data model

        Args:
            data_model_list: List of VRF dicts from the rendered data model.

        Returns:
            List of VRF dicts formatted for dcnm_vrf state: deleted.
        """
        result = self.executor.execute_rest(
            "GET",
            f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/v2"
            f"/fabrics/{self.fabric_name}/vrfs",
        )

        controller_vrfs = []
        try:
            response = result.get('response', {})
            data = response.get('DATA', response)
            if isinstance(data, str):
                import json
                data = json.loads(data)
            if isinstance(data, list):
                controller_vrfs = data
        except (KeyError, TypeError, ValueError):
            display.warning(
                f"REMOVE [{self.fabric_name}] Failed to parse VRF response "
                f"— skipping controller diff for VRFs"
            )
            return []

        # Build data model set of VRF names
        dm_vrf_names = frozenset(
            vrf.get('vrf_name', '') for vrf in data_model_list if vrf.get('vrf_name')
        )

        # Diff: controller VRFs not in data model
        items_to_delete = []
        for ctrl_vrf in controller_vrfs:
            vrf_name = ctrl_vrf.get('vrfName', '')
            if vrf_name and vrf_name not in dm_vrf_names:
                items_to_delete.append({
                    'vrf_name': vrf_name,
                })

        display.v(
            f"REMOVE [{self.fabric_name}] Controller diff for VRFs: "
            f"{len(controller_vrfs)} on controller, "
            f"{len(dm_vrf_names)} in data model, "
            f"{len(items_to_delete)} to delete"
        )

        return items_to_delete

    def _controller_diff_networks(self, data_model_list):
        """
        Query NDFC for all networks and return those not in the data model.

        Strategy:
          1. Query top-down network API for current fabric
          2. Build set of network names from data model
          3. Return controller networks absent from data model

        Args:
            data_model_list: List of network dicts from the rendered data model.

        Returns:
            List of network dicts formatted for dcnm_network state: deleted.
        """
        result = self.executor.execute_rest(
            "GET",
            f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/v2"
            f"/fabrics/{self.fabric_name}/networks",
        )

        controller_networks = []
        try:
            response = result.get('response', {})
            data = response.get('DATA', response)
            if isinstance(data, str):
                import json
                data = json.loads(data)
            if isinstance(data, list):
                controller_networks = data
        except (KeyError, TypeError, ValueError):
            display.warning(
                f"REMOVE [{self.fabric_name}] Failed to parse network response "
                f"— skipping controller diff for networks"
            )
            return []

        # Build data model set of network names
        dm_net_names = frozenset(
            net.get('net_name', '') for net in data_model_list if net.get('net_name')
        )

        # Diff: controller networks not in data model
        items_to_delete = []
        for ctrl_net in controller_networks:
            net_name = ctrl_net.get('networkName', '')
            if net_name and net_name not in dm_net_names:
                items_to_delete.append({
                    'net_name': net_name,
                })

        display.v(
            f"REMOVE [{self.fabric_name}] Controller diff for networks: "
            f"{len(controller_networks)} on controller, "
            f"{len(dm_net_names)} in data model, "
            f"{len(items_to_delete)} to delete"
        )

        return items_to_delete


class ActionModule(DtcPipelineActionBase):
    """
    Ansible ActionBase wrapper for remove_resources.

    Delegates to ResourceRemover via the DtcPipelineActionBase framework.
    """

    OPERATION_LABEL = 'Remove resources'

    def _create_runner(self, params, executor, task_vars):
        return ResourceRemover(params, executor, task_vars)

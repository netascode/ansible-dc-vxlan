# Analysis & Design: Consolidating DTC Roles into Pythonic Action Plugins

## Current Architecture Summary

The `dtc` directory contains 5 roles forming this dependency chain:

```
common_global
    └── common  (depends on common_global)
    └── connectivity_check  (depends on common_global)

create / deploy / remove  (each depends on connectivity_check + validate + common)
```

The execution lifecycle is: **validate → common → create → deploy → remove**

### Role Dependency Map

| Role | Dependencies | Purpose |
|------|-------------|---------|
| `dtc/common` | `common_global` | Renders Jinja2 templates to YAML, diffs against previous run, sets change flags |
| `dtc/connectivity_check` | `common_global` | Verifies NDFC connectivity and authorization, retrieves ND/NDFC versions |
| `dtc/create` | `connectivity_check`, `validate`, `common` | Creates/updates NDFC resources (fabrics, devices, interfaces, VRFs, networks, policies) |
| `dtc/deploy` | `connectivity_check`, `validate`, `common` | Deploys fabric config (config-save, config-deploy, sync-check) |
| `dtc/remove` | `connectivity_check`, `validate`, `common` | Removes unmanaged resources from NDFC |

### Existing Python Plugins

| Plugin | Location | Purpose |
|--------|----------|---------|
| `fabric_deploy_manager.py` | `plugins/action/dtc/` | Manages fabric config-save, deploy, sync-check lifecycle |
| `diff_compare.py` | `plugins/action/dtc/` | Structural diff of YAML files (updated/removed/equal items) |
| `diff_model_changes.py` | `plugins/action/dtc/` | MD5-based change detection between old and new rendered files |
| `change_flag_manager.py` | `plugins/action/common/` | Manages per-fabric-type change detection flags via JSON on disk |
| `prepare_service_model.py` | `plugins/action/common/` | Plugin pipeline for data model preparation (prep_001→prep_999) |
| `run_map.py` | `plugins/action/common/` | Tracks role execution stages for diff-run feature |
| `helper_functions.py` | `plugins/plugin_utils/` | Shared NDFC API helpers (get switch policy, fabric attributes, etc.) |
| `data_model_keys.py` | `plugins/plugin_utils/` | Registry of data model key paths per fabric type |

---

## Identified Patterns (Candidates for Python Consolidation)

After analyzing ~50 YAML task files and ~30 Python plugins, there are **4 dominant patterns** repeated across every fabric type and every role:

---

### Pattern 1: Template-Render-Diff-Flag Cycle (Common Role)

This is the single most repeated pattern — it appears **20+ times** in the common role alone. Every resource type (fabric, inventory, interfaces, VRFs, networks, VPC peering, policies, links, edge connections, underlay IP) follows the exact same 7-step sequence:

```
1. set_fact: file_name
2. stat: previous file
3. copy: backup previous → .old
4. file: delete previous
5. template: render Jinja2 → new YAML file
6. set_fact: load rendered YAML into variable
7. diff_model_changes: MD5-compare .old vs new → set change flag
```

This is currently ~50 lines of YAML per resource type × ~20 resource types = **~1000 lines of repetitive YAML**.

**Example from `common/tasks/common/ndfc_fabric.yml`:**

```yaml
- name: Set file_name Var
  ansible.builtin.set_fact:
    file_name: "ndfc_fabric.yml"

- name: Stat Previous File If It Exists
  ansible.builtin.stat:
    path: "{{ path_name }}{{ file_name }}"
  register: data_file_previous

- name: Backup Previous Data File If It Exists
  ansible.builtin.copy:
    src: "{{ path_name }}{{ file_name }}"
    dest: "{{ path_name }}{{ file_name }}.old"
    mode: preserve
  when: data_file_previous.stat.exists

- name: Delete Previous Data File If It Exists
  ansible.builtin.file:
    state: absent
    path: "{{ path_name }}{{ file_name }}"
  when: data_file_previous.stat.exists

- name: Build Fabric Creation Parameters From Template
  ansible.builtin.template:
    src: ndfc_fabric.j2
    dest: "{{ path_name }}{{ file_name }}"
    mode: '0644'

- name: Set fabric_config Var
  ansible.builtin.set_fact:
    fabric_config: "{{ lookup('file', path_name + file_name) | from_yaml }}"

- name: Diff Previous and Current Data Files
  cisco.nac_dc_vxlan.dtc.diff_model_changes:
    file_name_previous: "{{ path_name }}{{ file_name }}.old"
    file_name_current: "{{ path_name }}{{ file_name }}"
  register: file_diff_result

- name: Set File Change Flag Based on File Diff Result
  cisco.nac_dc_vxlan.common.change_flag_manager:
    fabric_type: "{{ data_model_extended.vxlan.fabric.type }}"
    fabric_name: "{{ data_model_extended.vxlan.fabric.name }}"
    role_path: "{{ common_role_path }}"
    operation: update
    change_flag: changes_detected_fabric
    flag_value: true
  when:
    - file_diff_result.file_data_changed
    - check_roles['save_previous']
```

This exact pattern is duplicated for every resource type with only the file name, template name, and flag name changing.

---

### Pattern 2: Fabric-Type Dispatch (All Roles)

Every `main.yml` and every `interfaces.yml` / `fabric.yml` in create/remove has this:

```yaml
- set_fact: vars_common_local = vars_common_vxlan
  when: type == "VXLAN_EVPN"
- set_fact: vars_common_local = vars_common_ebgp_vxlan
  when: type == "eBGP_VXLAN"
- set_fact: vars_common_local = vars_common_isn
  when: type == "ISN"
- set_fact: vars_common_local = vars_common_msd
  when: type == "MSD"
- set_fact: vars_common_local = vars_common_external
  when: type == "External"
```

This is a classic polymorphic dispatch that should be a Python dict lookup.

---

### Pattern 3: Conditional Resource Management (Create/Remove Roles)

The create and remove roles conditionally call `cisco.dcnm.*` modules based on `change_flags.*` booleans and `data_model_extended` state. Each fabric type has its own `sub_main_*.yml` with near-identical structure.

**Example from `create/tasks/sub_main_vxlan.yml`:**

```yaml
- name: Create iBGP VXLAN Fabric in Nexus Dashboard
  ansible.builtin.import_tasks: common/fabric.yml
  when:
    - data_model_extended.vxlan.fabric.name is defined
    - data_model_extended.vxlan.fabric.type == "VXLAN_EVPN"
    - change_flags.changes_detected_fabric

- name: Manage iBGP VXLAN Fabric Switches in Nexus Dashboard
  ansible.builtin.import_tasks: common/devices.yml
  when:
    - data_model_extended.vxlan.topology.switches | length > 0
    - change_flags.changes_detected_inventory

- name: Manage iBGP VXLAN Fabric Interfaces in Nexus Dashboard
  ansible.builtin.import_tasks: common/interfaces.yml
  when:
    - data_model_extended.vxlan.topology.interfaces.modes.all.count > 0
    - change_flags.changes_detected_interfaces

# ... repeated for VRFs, networks, links, policies, edge connections
```

---

### Pattern 4: Deploy Orchestration

The deploy role calls `fabric_deploy_manager` (already a Python action plugin) with fabric-type-specific parameters. This is **already well-abstracted** and serves as a good reference for how the other roles should look.

---

## Proposed Architecture: 3 Consolidated Action Plugins

```
plugins/action/dtc/
├── build_resource_data.py        # NEW — replaces common role's template+diff+flag cycle
├── manage_resources.py           # NEW — replaces create role's conditional NDFC calls
├── remove_resources.py           # NEW — replaces remove role's conditional NDFC calls
├── fabric_deploy_manager.py      # EXISTING — already Pythonic, keep as-is
├── diff_compare.py               # EXISTING — absorbed into build_resource_data
├── diff_model_changes.py         # EXISTING — absorbed into build_resource_data
└── ... (other existing plugins)

plugins/plugin_utils/
├── resource_builder.py           # NEW — core rendering + diff engine
├── fabric_type_registry.py       # NEW — fabric-type polymorphism
├── ndfc_resource_manager.py      # NEW — unified NDFC API interaction
├── helper_functions.py           # EXISTING
└── data_model_keys.py            # EXISTING
```

---

### Plugin 1: `build_resource_data` — The Resource Builder

**Replaces:** The entire `dtc/common` role's `sub_main_*.yml` and ~20 task files in `tasks/common/` and `tasks/vxlan/`

**Design:**

```python
# plugins/action/dtc/build_resource_data.py

class ResourceBuilder:
    """
    Consolidates the Template→Render→Diff→Flag cycle for all resource types.

    Replaces ~1000 lines of repetitive YAML with a data-driven pipeline.
    """

    # Registry of all resource types and their rendering config
    RESOURCE_TYPES = {
        'fabric': {
            'template': 'ndfc_fabric.j2',
            'output_file': 'ndfc_fabric.yml',
            'change_flag': 'changes_detected_fabric',
            'diff_compare': False,  # No structural diff needed, just MD5
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'MSD', 'MCFG', 'External'],
        },
        'inventory': {
            'template': 'ndfc_inventory.j2',
            'output_file': 'ndfc_inventory.yml',
            'change_flag': 'changes_detected_inventory',
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'],
            'pre_hooks': ['get_poap_data'],
            'post_hooks': ['get_credentials'],
        },
        'inventory_no_bootstrap': {
            'template': 'ndfc_inventory_no_bootstrap.j2',
            'output_file': 'ndfc_inventory_no_bootstrap.yml',
            'change_flag': None,  # No separate flag, shares with inventory
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'],
        },
        'vpc_domain_id_resource': {
            'template': 'ndfc_vpc/ndfc_vpc_domain_id_resource.j2',
            'output_file': 'ndfc_vpc_domain_id_resource.yml',
            'change_flag': 'changes_detected_vpc_domain_id_resource',
            'diff_compare': True,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN'],
        },
        'vpc_peering': {
            'template': 'ndfc_vpc/ndfc_vpc_peering_pairs.j2',
            'output_file': 'ndfc_vpc_peering.yml',
            'change_flag': 'changes_detected_vpc_peering',
            'diff_compare': True,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN'],
        },
        'vpc_fabric_peering_links': {
            'template': 'ndfc_vpc/ndfc_vpc_fabric_peering_links.j2',
            'output_file': 'ndfc_link_vpc_peering.yml',
            'change_flag': 'changes_detected_link_vpc_peering',
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN'],
        },
        'vrfs': {
            'template': 'ndfc_attach_vrfs.j2',
            'output_file': 'ndfc_attach_vrfs.yml',
            'change_flag': 'changes_detected_vrfs',
            'diff_compare': True,  # Needs structural diff for targeted updates
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN'],
        },
        'networks': {
            'template': 'ndfc_attach_networks.j2',
            'output_file': 'ndfc_attach_networks.yml',
            'change_flag': 'changes_detected_networks',
            'diff_compare': True,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN'],
        },
        'interface_breakout': {
            'template': 'ndfc_interfaces/ndfc_interface_breakout.j2',
            'output_file': 'ndfc_interface_breakout.yml',
            'change_flag': 'changes_detected_interface_breakout',
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'],
        },
        'interface_breakout_preprov': {
            'template': 'ndfc_interfaces/ndfc_interface_breakout_preprov.j2',
            'output_file': 'ndfc_interface_breakout_preprov.yml',
            'change_flag': 'changes_detected_interface_breakout_preprov',
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'],
        },
        'interface_loopback': {
            'template': 'ndfc_interfaces/ndfc_loopback_interfaces.j2',
            'output_file': 'ndfc_loopback_interfaces.yml',
            'change_flag': 'changes_detected_interface_loopback',
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'],
        },
        'interface_access_po': {
            'template': 'ndfc_interfaces/ndfc_interface_access_po.j2',
            'output_file': 'ndfc_interface_access_po.yml',
            'change_flag': 'changes_detected_interface_access_po',
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'],
        },
        'interface_trunk_po': {
            'template': 'ndfc_interfaces/ndfc_interface_trunk_po.j2',
            'output_file': 'ndfc_interface_trunk_po.yml',
            'change_flag': 'changes_detected_interface_trunk_po',
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'],
        },
        'interface_routed': {
            'template': 'ndfc_interfaces/ndfc_interface_routed.j2',
            'output_file': 'ndfc_interface_routed.yml',
            'change_flag': 'changes_detected_interface_routed',
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'],
        },
        'sub_interface_routed': {
            'template': 'ndfc_interfaces/ndfc_sub_interface_routed.j2',
            'output_file': 'ndfc_sub_interface_routed.yml',
            'change_flag': 'changes_detected_sub_interface_routed',
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'],
        },
        'interface_po_routed': {
            'template': 'ndfc_interfaces/ndfc_interface_po_routed.j2',
            'output_file': 'ndfc_interface_po_routed.yml',
            'change_flag': 'changes_detected_interface_po_routed',
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'],
        },
        'interface_trunk': {
            'template': 'ndfc_interfaces/ndfc_interface_trunk.j2',
            'output_file': 'ndfc_interface_trunk.yml',
            'change_flag': 'changes_detected_interface_trunk',
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'],
        },
        'interface_access': {
            'template': 'ndfc_interfaces/ndfc_interface_access.j2',
            'output_file': 'ndfc_interface_access.yml',
            'change_flag': 'changes_detected_interface_access',
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'],
        },
        'interface_dot1q': {
            'template': 'ndfc_interfaces/ndfc_interface_dot1q.j2',
            'output_file': 'ndfc_interface_dot1q.yml',
            'change_flag': 'changes_detected_interface_dot1q',
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'],
        },
        'interface_vpc': {
            'template': 'ndfc_interfaces/ndfc_interface_vpc.j2',
            'output_file': 'ndfc_interface_vpc.yml',
            'change_flag': 'changes_detected_interface_vpc',
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'],
        },
        'policy': {
            'template': 'ndfc_policy.j2',
            'output_file': 'ndfc_policy.yml',
            'change_flag': 'changes_detected_policy',
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'],
        },
        'fabric_links': {
            'template': 'ndfc_fabric_links.j2',
            'output_file': 'ndfc_fabric_links.yml',
            'change_flag': 'changes_detected_fabric_links',
            'diff_compare': True,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN'],
        },
        'underlay_ip_address': {
            'template': 'ndfc_underlay_ip_address.j2',
            'output_file': 'ndfc_underlay_ip_address.yml',
            'change_flag': 'changes_detected_underlay_ip_address',
            'diff_compare': True,
            'fabric_types': ['VXLAN_EVPN'],
        },
        'edge_connections': {
            'template': 'ndfc_edge_connections.j2',
            'output_file': 'ndfc_edge_connections.yml',
            'change_flag': 'changes_detected_edge_connections',
            'diff_compare': False,
            'fabric_types': ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External'],
        },
        # MSD-specific resources
        'msd_child_fabrics': {
            'template': 'ndfc_child_fabrics.j2',  # MSD-specific
            'output_file': 'ndfc_child_fabrics.yml',
            'change_flag': None,
            'diff_compare': False,
            'fabric_types': ['MSD'],
        },
        'bgw_anycast_vip': {
            'template': 'ndfc_bgw_anycast_vip.j2',
            'output_file': 'ndfc_bgw_anycast_vip.yml',
            'change_flag': 'changes_detected_bgw_anycast_vip',
            'diff_compare': False,
            'fabric_types': ['MSD'],
        },
    }

    def __init__(self, fabric_type, fabric_name, data_model, role_path,
                 check_roles, force_run_all, run_map_diff_run):
        self.fabric_type = fabric_type
        self.fabric_name = fabric_name
        self.data_model = data_model
        self.role_path = role_path
        self.check_roles = check_roles
        self.force_run_all = force_run_all
        self.run_map_diff_run = run_map_diff_run
        self.change_flags = ChangeDetectionManager(...)

    def build_all(self) -> dict:
        """
        Build all resource data for the given fabric type.
        Returns a dict of {resource_name: rendered_data} plus change flags.
        """
        results = {}
        applicable_resources = [
            (name, cfg) for name, cfg in self.RESOURCE_TYPES.items()
            if self.fabric_type in cfg['fabric_types']
        ]

        for resource_name, config in applicable_resources:
            result = self._build_single_resource(resource_name, config)
            results[resource_name] = result

        # Build the composite interface_all from individual interface results
        if self.fabric_type in ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External']:
            results['interface_all'] = self._build_interface_all(results)

        return {
            'resource_data': results,
            'change_flags': self.change_flags.get_all(),
        }

    def _build_single_resource(self, resource_name, config):
        """
        Execute the full Template→Render→Diff→Flag pipeline for one resource.
        Replaces ~50 lines of YAML per resource type.
        """
        output_path = f"{self.role_path}/files/{self._fabric_subdir()}/{self.fabric_name}"
        file_path = f"{output_path}/{config['output_file']}"
        old_path = f"{file_path}.old"

        # 1. Backup previous file
        self._backup_file(file_path, old_path)

        # 2. Render Jinja2 template → YAML
        template = self._resolve_template(config['template'])
        rendered = self._render_template(template, self.data_model)
        self._write_file(file_path, rendered)

        # 3. Load rendered data
        resource_data = yaml.safe_load(rendered) or []

        # 4. MD5 diff check
        changed = self._check_md5_diff(old_path, file_path)
        if changed and config.get('change_flag'):
            self.change_flags.update(config['change_flag'], True)

        # 5. Structural diff (if needed for targeted create/remove)
        diff_result = None
        if config.get('diff_compare') and os.path.exists(old_path):
            diff_result = DiffCompare.compare_files(old_path, file_path)

        # 6. Cleanup
        self._cleanup_old(old_path, changed)

        return {
            'data': resource_data,
            'changed': changed,
            'diff': diff_result,
        }

    def _build_interface_all(self, results):
        """
        Compose the interface_all list from individual interface results.
        Replaces the ndfc_interface_all.yml task file.
        """
        interface_types = [
            'interface_breakout', 'interface_breakout_preprov',
            'interface_trunk', 'interface_routed', 'sub_interface_routed',
            'interface_access', 'interface_trunk_po', 'interface_access_po',
            'interface_po_routed', 'interface_loopback', 'interface_dot1q',
            'interface_vpc'
        ]

        all_create = []
        all_remove_overridden = []
        for itype in interface_types:
            if itype in results:
                data = results[itype].get('data', [])
                all_create.extend(data)
                all_remove_overridden.extend(data)

        # Run structural diff on the composite
        # ... (save to file, compare with old, etc.)

        return {
            'data_create': all_create,
            'data_remove_overridden': all_remove_overridden,
            'changed': any(results.get(t, {}).get('changed', False) for t in interface_types),
            'diff': None,  # computed from composite file
        }

    def _fabric_subdir(self):
        """Map fabric type to file subdirectory."""
        SUBDIR_MAP = {
            'VXLAN_EVPN': 'vxlan',
            'eBGP_VXLAN': 'vxlan',
            'ISN': 'isn',
            'MSD': 'msd',
            'MCFG': 'mcfg',
            'External': 'vxlan',
        }
        return SUBDIR_MAP.get(self.fabric_type, 'vxlan')

    def _backup_file(self, file_path, old_path):
        """Backup existing file to .old extension."""
        if os.path.exists(file_path):
            shutil.copy2(file_path, old_path)
            os.remove(file_path)

    def _check_md5_diff(self, old_path, new_path):
        """MD5-based change detection with omit_placeholder normalization."""
        if not os.path.exists(old_path):
            return True

        with open(old_path, 'r') as f:
            old_data = f.read()
        with open(new_path, 'r') as f:
            new_data = f.read()

        # Normalize omit placeholders
        pattern = r'__omit_place_holder__\S+'
        old_normalized = re.sub(pattern, 'NORMALIZED', old_data)
        new_normalized = re.sub(pattern, 'NORMALIZED', new_data)

        old_md5 = hashlib.md5(old_normalized.encode()).hexdigest()
        new_md5 = hashlib.md5(new_normalized.encode()).hexdigest()

        return old_md5 != new_md5

    def _cleanup_old(self, old_path, changed):
        """Remove .old file if no changes detected."""
        if not changed and os.path.exists(old_path):
            os.remove(old_path)
```

**Key benefits:**
- **~1000 lines of YAML → ~200 lines of Python** (the data-driven registry + generic pipeline)
- Adding a new resource type = adding 6-8 lines to the `RESOURCE_TYPES` dict instead of copying 50 lines of YAML
- Jinja2 rendering remains (templates are still external), but the orchestration around it is pure Python
- Change detection logic is centralized, not scattered across task files

---

### Plugin 2: `manage_resources` — The Resource Creator

**Replaces:** The `dtc/create` role's `sub_main_*.yml` files and task files in `tasks/common/` and `tasks/common_vxlan/`

**Design:**

```python
# plugins/action/dtc/manage_resources.py

class ResourceManager:
    """
    Manages the ordered creation of NDFC resources for any fabric type.

    Replaces the create role's per-fabric-type sub_main files and
    the conditional cisco.dcnm module calls.
    """

    # Ordered pipeline of resource operations per fabric type
    CREATE_PIPELINES = {
        'VXLAN_EVPN': [
            # (resource_name,    module_name,                state,      change_flag_guard)
            ('fabric',           'dcnm_fabric',              'merged',   'changes_detected_fabric'),
            ('devices',          'dcnm_inventory',           'merged',   'changes_detected_inventory'),
            ('vpc_peering',      'dcnm_links',               'merged',   'changes_detected_vpc_peering'),
            ('config_save',      '_config_save',             None,       'changes_detected_vpc_peering'),
            ('interfaces',       'dcnm_interface',           'replaced', 'changes_detected_interfaces'),
            ('edge_connections', 'dcnm_links',               'merged',   'changes_detected_edge_connections'),
            ('vrfs_networks',    '_vrfs_networks_pipeline',  None,       'changes_detected_vrfs'),
            ('links',            'dcnm_links',               'merged',   'changes_detected_fabric_links'),
            ('policies',         'dcnm_policy',              'merged',   'changes_detected_policy'),
        ],
        'eBGP_VXLAN': [
            ('fabric',           'dcnm_fabric',              'merged',   'changes_detected_fabric'),
            ('devices',          'dcnm_inventory',           'merged',   'changes_detected_inventory'),
            ('vpc_peering',      'dcnm_links',               'merged',   'changes_detected_vpc_peering'),
            ('config_save',      '_config_save',             None,       'changes_detected_vpc_peering'),
            ('interfaces',       'dcnm_interface',           'replaced', 'changes_detected_interfaces'),
            ('edge_connections', 'dcnm_links',               'merged',   'changes_detected_edge_connections'),
            ('vrfs_networks',    '_vrfs_networks_pipeline',  None,       'changes_detected_vrfs'),
            ('links',            'dcnm_links',               'merged',   'changes_detected_fabric_links'),
            ('policies',         'dcnm_policy',              'merged',   'changes_detected_policy'),
        ],
        'ISN': [
            ('fabric',           'dcnm_fabric',              'merged',   'changes_detected_fabric'),
            ('devices',          'dcnm_inventory',           'merged',   'changes_detected_inventory'),
            ('interfaces',       'dcnm_interface',           'replaced', 'changes_detected_interfaces'),
            ('edge_connections', 'dcnm_links',               'merged',   'changes_detected_edge_connections'),
            ('policies',         'dcnm_policy',              'merged',   'changes_detected_policy'),
        ],
        'External': [
            ('fabric',           'dcnm_fabric',              'merged',   'changes_detected_fabric'),
            ('devices',          'dcnm_inventory',           'merged',   'changes_detected_inventory'),
            ('interfaces',       'dcnm_interface',           'replaced', 'changes_detected_interfaces'),
            ('edge_connections', 'dcnm_links',               'merged',   'changes_detected_edge_connections'),
            ('policies',         'dcnm_policy',              'merged',   'changes_detected_policy'),
        ],
        'MSD': [
            ('fabric',           'dcnm_fabric',              'merged',   'changes_detected_fabric'),
            ('child_fabrics',    '_manage_child_fabrics',    None,       None),
            ('msite_data',       '_prepare_msite_data',      None,       None),
            ('bgw_anycast',      'dcnm_resource_manager',   'merged',   'changes_detected_bgw_anycast_vip'),
            ('vrfs_networks',    '_msd_vrfs_networks',       None,       None),
        ],
        'MCFG': [
            ('fabric',           'dcnm_fabric',              'merged',   'changes_detected_fabric'),
            ('child_fabrics',    '_manage_child_fabrics',    None,       None),
            ('msite_data',       '_prepare_msite_data',      None,       None),
            ('vrfs_networks',    '_mcfg_vrfs_networks',      None,       None),
        ],
    }

    def create(self, fabric_type, resource_data, change_flags, data_model):
        """Execute the ordered creation pipeline for the given fabric type."""
        pipeline = self.CREATE_PIPELINES[fabric_type]

        for resource_name, module, state, flag_name in pipeline:
            # Skip if no changes detected for this resource
            if flag_name and not change_flags.get(flag_name, False):
                continue

            # Skip if prerequisite data is empty
            data = resource_data.get(resource_name, {}).get('data', [])
            if not data and not module.startswith('_'):
                continue

            if module.startswith('_'):
                # Internal method call (config_save, prepare_msite_data, etc.)
                getattr(self, module)(resource_name, data, data_model)
            else:
                # Ansible module call via _execute_module
                self._execute_ndfc_module(
                    module_name=f"cisco.dcnm.{module}",
                    state=state,
                    config=data,
                    fabric_name=data_model['vxlan']['fabric']['name'],
                )

    def _execute_ndfc_module(self, module_name, state, config, fabric_name):
        """Execute an NDFC Ansible module via _execute_module."""
        module_args = {
            'fabric': fabric_name,
            'state': state,
            'config': config,
        }
        return self.action_module._execute_module(
            module_name=module_name,
            module_args=module_args,
            task_vars=self.task_vars,
            tmp=self.tmp,
        )

    def _config_save(self, resource_name, data, data_model):
        """Execute a config-save POST to NDFC."""
        fabric_name = data_model['vxlan']['fabric']['name']
        path = f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/{fabric_name}/config-save"
        return self.action_module._execute_module(
            module_name="cisco.dcnm.dcnm_rest",
            module_args={"method": "POST", "path": path},
            task_vars=self.task_vars,
            tmp=self.tmp,
        )
```

---

### Plugin 3: `remove_resources` — The Resource Remover

**Replaces:** The `dtc/remove` role's `sub_main_*.yml` files

**Design mirrors `manage_resources`** but with reversed ordering and `deleted`/`overridden` states:

```python
# plugins/action/dtc/remove_resources.py

class ResourceRemover:
    """
    Manages the ordered removal of unmanaged NDFC resources.

    Removal order is the reverse of creation to respect dependencies
    (e.g., remove networks before VRFs, remove interfaces before switches).
    """

    REMOVE_PIPELINES = {
        'VXLAN_EVPN': [
            # Reverse order of creation to respect dependencies
            ('edge_connections', 'dcnm_links',      'deleted',    'changes_detected_edge_connections'),
            ('policies',         'dcnm_policy',      'deleted',    'changes_detected_policy'),
            ('interfaces',       'dcnm_interface',   'deleted',    'changes_detected_interfaces'),
            ('networks',         'dcnm_network',     'deleted',    'changes_detected_networks'),
            ('vrfs',             'dcnm_vrf',         'deleted',    'changes_detected_vrfs'),
            ('links',            'dcnm_links',       'deleted',    'changes_detected_fabric_links'),
            ('vpc_peers',        'dcnm_links',       'deleted',    'changes_detected_vpc_peering'),
            ('switches',         'dcnm_inventory',   'deleted',    'changes_detected_inventory'),
        ],
        'eBGP_VXLAN': [
            ('edge_connections', 'dcnm_links',      'deleted',    'changes_detected_edge_connections'),
            ('policies',         'dcnm_policy',      'deleted',    'changes_detected_policy'),
            ('interfaces',       'dcnm_interface',   'deleted',    'changes_detected_interfaces'),
            ('networks',         'dcnm_network',     'deleted',    'changes_detected_networks'),
            ('vrfs',             'dcnm_vrf',         'deleted',    'changes_detected_vrfs'),
            ('links',            'dcnm_links',       'deleted',    'changes_detected_fabric_links'),
            ('vpc_peers',        'dcnm_links',       'deleted',    'changes_detected_vpc_peering'),
            ('switches',         'dcnm_inventory',   'deleted',    'changes_detected_inventory'),
        ],
        'ISN': [
            ('edge_connections', 'dcnm_links',      'deleted',    'changes_detected_edge_connections'),
            ('policies',         'dcnm_policy',      'deleted',    'changes_detected_policy'),
            ('interfaces',       'dcnm_interface',   'deleted',    'changes_detected_interfaces'),
            ('switches',         'dcnm_inventory',   'deleted',    'changes_detected_inventory'),
        ],
        'External': [
            ('edge_connections', 'dcnm_links',      'deleted',    'changes_detected_edge_connections'),
            ('policies',         'dcnm_policy',      'deleted',    'changes_detected_policy'),
            ('interfaces',       'dcnm_interface',   'deleted',    'changes_detected_interfaces'),
            ('switches',         'dcnm_inventory',   'deleted',    'changes_detected_inventory'),
        ],
        'MSD': [
            ('networks',         'dcnm_network',    'deleted',    'changes_detected_networks'),
            ('vrfs',             'dcnm_vrf',        'deleted',    'changes_detected_vrfs'),
            ('child_fabrics',    '_remove_child_fabrics', None,    None),
        ],
        'MCFG': [
            ('networks',         'dcnm_network',    'deleted',    'changes_detected_networks'),
            ('vrfs',             'dcnm_vrf',        'deleted',    'changes_detected_vrfs'),
            ('child_fabrics',    '_remove_child_fabrics', None,    None),
        ],
    }

    def remove(self, fabric_type, resource_data, change_flags, data_model,
               run_map_diff_run, force_run_all, interface_delete_mode):
        """Execute the ordered removal pipeline for the given fabric type."""
        pipeline = self.REMOVE_PIPELINES[fabric_type]

        for resource_name, module, state, flag_name in pipeline:
            if flag_name and not change_flags.get(flag_name, False):
                continue

            # For interfaces, use diff_result.removed when diff_run is active
            if resource_name == 'interfaces':
                data = self._get_interface_remove_data(
                    resource_data, run_map_diff_run, force_run_all, interface_delete_mode
                )
                if not data:
                    continue
                if run_map_diff_run and not force_run_all:
                    state = 'deleted'
                else:
                    state = 'overridden'
            else:
                data = resource_data.get(resource_name, {}).get('diff', {}).get('removed', [])
                if not data:
                    data = resource_data.get(resource_name, {}).get('data', [])

            if not data:
                continue

            if module.startswith('_'):
                getattr(self, module)(resource_name, data, data_model)
            else:
                self._execute_ndfc_module(
                    module_name=f"cisco.dcnm.{module}",
                    state=state,
                    config=data,
                    fabric_name=data_model['vxlan']['fabric']['name'],
                    deploy=False,  # Remove role does not deploy by default
                )

    def _get_interface_remove_data(self, resource_data, run_map_diff_run,
                                   force_run_all, interface_delete_mode):
        """Determine interface removal dataset based on execution mode."""
        if not interface_delete_mode:
            return None

        interface_data = resource_data.get('interface_all', {})
        if run_map_diff_run and not force_run_all:
            return interface_data.get('diff', {}).get('removed', [])
        else:
            return interface_data.get('data_remove_overridden', [])
```

---

## Plugin Utilities Layer

### `fabric_type_registry.py`

```python
# plugins/plugin_utils/fabric_type_registry.py

class FabricTypeRegistry:
    """
    Eliminates the repeated when: fabric_type == 'X' patterns.
    Maps fabric types to their namespace variables, templates, and behaviors.
    """

    REGISTRY = {
        'VXLAN_EVPN': {
            'namespace': 'vars_common_vxlan',
            'file_subdir': 'vxlan',
            'global_key': 'ibgp',
            'fabric_template_dir': 'dc_vxlan_fabric',
            'supports_overlay': True,
            'supports_vpc': True,
            'supports_multisite': False,
        },
        'eBGP_VXLAN': {
            'namespace': 'vars_common_ebgp_vxlan',
            'file_subdir': 'vxlan',
            'global_key': 'ebgp',
            'fabric_template_dir': 'ebgp_vxlan_fabric',
            'supports_overlay': True,
            'supports_vpc': True,
            'supports_multisite': False,
        },
        'ISN': {
            'namespace': 'vars_common_isn',
            'file_subdir': 'isn',
            'global_key': None,
            'fabric_template_dir': 'isn_fabric',
            'supports_overlay': False,
            'supports_vpc': False,
            'supports_multisite': False,
        },
        'MSD': {
            'namespace': 'vars_common_msd',
            'file_subdir': 'msd',
            'global_key': None,
            'fabric_template_dir': 'msd_fabric',
            'supports_overlay': False,
            'supports_vpc': False,
            'supports_multisite': True,
        },
        'MCFG': {
            'namespace': 'vars_common_mcfg',
            'file_subdir': 'mcfg',
            'global_key': None,
            'fabric_template_dir': 'mcfg_fabric',
            'supports_overlay': False,
            'supports_vpc': False,
            'supports_multisite': True,
        },
        'External': {
            'namespace': 'vars_common_external',
            'file_subdir': 'vxlan',
            'global_key': None,
            'fabric_template_dir': 'dc_external_fabric',
            'supports_overlay': False,
            'supports_vpc': True,
            'supports_multisite': False,
        },
    }

    @classmethod
    def get(cls, fabric_type: str) -> dict:
        """Get the full config for a fabric type."""
        if fabric_type not in cls.REGISTRY:
            raise ValueError(f"Unknown fabric type: {fabric_type}")
        return cls.REGISTRY[fabric_type]

    @classmethod
    def resolve_namespace(cls, fabric_type: str, all_vars: dict) -> dict:
        """
        Replace the 5-way when/set_fact pattern with a single lookup.

        Before (YAML):
            - set_fact: vars_common_local = vars_common_vxlan
              when: type == "VXLAN_EVPN"
            - set_fact: vars_common_local = vars_common_ebgp_vxlan
              when: type == "eBGP_VXLAN"
            ... (5 more)

        After (Python):
            vars_common_local = FabricTypeRegistry.resolve_namespace(fabric_type, task_vars)
        """
        ns = cls.REGISTRY[fabric_type]['namespace']
        return all_vars[ns]

    @classmethod
    def supports_feature(cls, fabric_type: str, feature: str) -> bool:
        """Check if a fabric type supports a specific feature."""
        config = cls.REGISTRY.get(fabric_type, {})
        return config.get(f'supports_{feature}', False)
```

---

## Simplified Role YAML After Consolidation

After the Python consolidation, the roles become thin orchestration wrappers:

### `roles/dtc/common/tasks/main.yml` (simplified)

```yaml
---
- name: Create Fact To Store Common Role Path
  ansible.builtin.set_fact:
    common_role_path: "{{ role_path }}"
  tags: "{{ nac_tags.common_role }}"

- name: Build All Resource Data For Fabric
  cisco.nac_dc_vxlan.dtc.build_resource_data:
    fabric_type: "{{ data_model_extended.vxlan.fabric.type }}"
    fabric_name: "{{ data_model_extended.vxlan.fabric.name }}"
    data_model: "{{ data_model_extended }}"
    role_path: "{{ common_role_path }}"
    check_roles: "{{ check_roles }}"
    force_run_all: "{{ force_run_all | default(false) }}"
    run_map_diff_run: "{{ run_map_read_result.diff_run }}"
  register: resource_build_result
  delegate_to: localhost
  tags: "{{ nac_tags.common_role }}"

- name: Store Resource Data and Change Flags
  ansible.builtin.set_fact:
    vars_common: "{{ resource_build_result.resource_data }}"
    change_flags: "{{ resource_build_result.change_flags }}"
  delegate_to: localhost
  tags: "{{ nac_tags.common_role }}"
```

### `roles/dtc/create/tasks/main.yml` (simplified)

```yaml
---
- name: Create Resources in Nexus Dashboard
  cisco.nac_dc_vxlan.dtc.manage_resources:
    fabric_type: "{{ data_model_extended.vxlan.fabric.type }}"
    fabric_name: "{{ data_model_extended.vxlan.fabric.name }}"
    data_model: "{{ data_model_extended }}"
    resource_data: "{{ vars_common }}"
    change_flags: "{{ change_flags }}"
    nd_version: "{{ nd_version }}"
  when: change_flags.changes_detected_any
  register: create_result
  tags: "{{ nac_tags.create }}"

- name: Mark Stage Role Create Completed
  cisco.nac_dc_vxlan.common.run_map:
    data_model: "{{ data_model_extended }}"
    stage: role_create_completed
  register: run_map
  delegate_to: localhost
```

### `roles/dtc/remove/tasks/main.yml` (simplified)

```yaml
---
- name: Remove Unmanaged Resources from Nexus Dashboard
  cisco.nac_dc_vxlan.dtc.remove_resources:
    fabric_type: "{{ data_model_extended.vxlan.fabric.type }}"
    fabric_name: "{{ data_model_extended.vxlan.fabric.name }}"
    data_model: "{{ data_model_extended }}"
    resource_data: "{{ vars_common }}"
    change_flags: "{{ change_flags }}"
    run_map_diff_run: "{{ run_map_read_result.diff_run }}"
    force_run_all: "{{ force_run_all | default(false) }}"
    interface_delete_mode: "{{ interface_delete_mode | default(false) }}"
    stage_remove: "{{ stage_remove | default(false) }}"
  when: change_flags.changes_detected_any
  register: remove_result
  tags: "{{ nac_tags.remove }}"

- name: Deploy Remove Changes (if not staging)
  cisco.nac_dc_vxlan.dtc.fabric_deploy_manager:
    fabric_name: "{{ data_model_extended.vxlan.fabric.name }}"
    fabric_type: "{{ data_model_extended.vxlan.fabric.type }}"
    operation: all
  when:
    - stage_remove is false|bool
    - change_flags.changes_detected_any
    - data_model_extended.vxlan.fabric.type in ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External']
  tags: "{{ nac_tags.remove }}"

- name: Mark Stage Role Remove Completed
  cisco.nac_dc_vxlan.common.run_map:
    data_model: "{{ data_model_extended }}"
    stage: role_remove_completed
  register: run_map
  delegate_to: localhost
```

This reduces each role from dozens of task files to **a handful of tasks** calling Python plugins.

---

## Migration Strategy

| Phase | Scope | Risk | Effort |
|-------|-------|------|--------|
| **Phase 1** | `FabricTypeRegistry` + refactor fabric-type dispatch in existing plugins | Low — no behavior change | Small |
| **Phase 2** | `build_resource_data` — consolidate the Template→Diff→Flag cycle | Medium — need to ensure Jinja2 rendering context matches | Large |
| **Phase 3** | `manage_resources` — consolidate create operations | Medium — need to preserve `_execute_module` call patterns | Medium |
| **Phase 4** | `remove_resources` — consolidate remove operations | Medium — reverse-order dependencies | Medium |
| **Phase 5** | Deprecate old role task files, update tests | Low | Small |

### Phase 1: FabricTypeRegistry (Low Risk)

- Create `plugins/plugin_utils/fabric_type_registry.py`
- Refactor existing action plugins to use the registry for namespace resolution
- No changes to role YAML files
- Validates the pattern before broader adoption

### Phase 2: build_resource_data (Core Change)

- Create `plugins/action/dtc/build_resource_data.py`
- Absorb `diff_compare.py` and `diff_model_changes.py` logic into the builder
- Absorb `change_flag_manager.py` into in-memory flag management
- Replace all `common/tasks/common/*.yml` and `common/tasks/vxlan/*.yml` with a single plugin call
- **Critical consideration:** Jinja2 template rendering currently uses Ansible's `template` module which provides access to all `task_vars`. The Python plugin will need to replicate this context when calling `self._templar.template()` or use `self._execute_module()` to delegate to the template module.

### Phase 3: manage_resources (Create)

- Create `plugins/action/dtc/manage_resources.py`
- Replaces all `create/tasks/sub_main_*.yml` files
- Replaces `create/tasks/common/*.yml` task files
- Pipeline-driven execution based on fabric type

### Phase 4: remove_resources (Remove)

- Create `plugins/action/dtc/remove_resources.py`
- Replaces all `remove/tasks/sub_main_*.yml` files
- Replaces `remove/tasks/common/*.yml` task files
- Reverse-ordered pipeline for safe dependency-aware removal

### Phase 5: Cleanup

- Archive/deprecate old task files
- Update integration tests
- Update documentation

---

## Key Design Decisions

1. **Jinja2 templates stay external** — They encode complex NDFC API payload structures and are best maintained as `.j2` files. Python handles orchestration, not rendering-content authorship.

2. **`_execute_module` remains the NDFC interaction layer** — The `cisco.dcnm.*` modules are the stable API boundary to NDFC. The action plugins use `self._execute_module()` to call them, preserving Ansible's connection/credential management.

3. **Change flags become an in-memory data structure** — Instead of writing JSON to disk and reading it back between tasks, the `build_resource_data` plugin can return the full flag state in its result dict. The on-disk persistence can be retained for debugging but is no longer the inter-task communication mechanism.

4. **The `diff_compare` and `diff_model_changes` logic merges into `ResourceBuilder`** — These are currently separate action plugins only because the YAML orchestration required separate task steps. In Python they're just method calls within the pipeline.

5. **Role YAML files remain as thin wrappers** — This preserves Ansible's role-based execution model (tags, `--start-at-task`, conditional execution with `when:`, etc.) while moving all logic into Python.

6. **The `fabric_deploy_manager` is already well-designed** — It's the template for how the other plugins should be structured. No refactoring needed there.

---

## Impact Summary

| Metric | Before | After |
|--------|--------|-------|
| YAML task files in `dtc/` roles | ~50 files | ~5 files (thin wrappers) |
| Lines of repetitive YAML | ~2500+ | ~100 |
| Python action plugins | 18 (dtc) + 8 (common) | 21 (dtc) + 8 (common) |
| Fabric-type dispatch blocks | ~30 (scattered across YAML) | 1 (FabricTypeRegistry) |
| Adding a new resource type | Copy 50 lines YAML + edit 3-4 files | Add 6-8 lines to RESOURCE_TYPES dict |
| Adding a new fabric type | Edit 10+ sub_main files | Add entry to FabricTypeRegistry + pipeline dicts |

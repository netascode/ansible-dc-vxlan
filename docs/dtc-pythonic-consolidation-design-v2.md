# Analysis & Design: Consolidating DTC Roles into Pythonic Action Plugins

> **v2 — YAML-Externalized Registries**
>
> This revision moves all data-driven constants (resource types, create/remove pipelines,
> fabric type registry) out of Python source code and into external YAML files under
> `objects/` within the `cisco.nac_dc_vxlan` collection. Python plugins load these
> registries at runtime, achieving full separation of configuration data from execution
> logic.
>
> Changes from v1 are marked with **[v2]** annotations.

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

**[v2]** All data-driven registries are externalized to YAML files under `objects/`.

All paths below are relative to the collection root:
`vxlan-as-code/collections/ansible_collections/cisco/nac_dc_vxlan/`

```
# cisco/nac_dc_vxlan collection root
plugins/action/dtc/
├── build_resource_data.py        # NEW — replaces common role's template+diff+flag cycle
├── manage_resources.py           # NEW — replaces create role's conditional NDFC calls
├── remove_resources.py           # NEW — replaces remove role's conditional NDFC calls
├── fabric_deploy_manager.py      # EXISTING — already Pythonic, keep as-is
├── diff_compare.py               # EXISTING — absorbed into build_resource_data
├── diff_model_changes.py         # EXISTING — absorbed into build_resource_data
└── ... (other existing plugins)

objects/                                                          # [v2] NEW
├── resource_types.yml            # Data-driven registry for build_resource_data
├── create_pipelines.yml          # Ordered create operations per fabric type
├── remove_pipelines.yml          # Ordered remove operations per fabric type
└── fabric_types.yml              # Fabric-type polymorphism registry

plugins/plugin_utils/
├── registry_loader.py            # [v2] NEW — generic YAML registry loader
├── resource_builder.py           # NEW — core rendering + diff engine
├── fabric_type_registry.py       # NEW — fabric-type polymorphism (loads from YAML)
├── ndfc_resource_manager.py      # NEW — unified NDFC API interaction
├── helper_functions.py           # EXISTING
└── data_model_keys.py            # EXISTING
```

---

### **[v2]** YAML Registry Files

All data-driven constants are externalized to YAML files under `objects/`. This means
adding a new resource type, a new fabric type, or modifying a pipeline requires editing
only YAML — no Python changes needed.

| YAML File | Consumed By | Purpose |
|-----------|-------------|---------|
| `objects/resource_types.yml` | `build_resource_data.py` | Template→Render→Diff→Flag pipeline config per resource type |
| `objects/create_pipelines.yml` | `manage_resources.py` | Ordered creation operations per fabric type |
| `objects/remove_pipelines.yml` | `remove_resources.py` | Ordered removal operations per fabric type |
| `objects/fabric_types.yml` | `fabric_type_registry.py` | Fabric-type namespace, features, and directory mappings |

### **[v2]** Generic Registry Loader

A shared utility loads and caches YAML registries so each plugin doesn't repeat file I/O logic:

```python
# plugins/plugin_utils/registry_loader.py

import os
import yaml
from functools import lru_cache

class RegistryLoader:
    """
    Generic loader for YAML registry files under objects/.

    Provides a single entry point for all plugins to load their
    data-driven configuration from external YAML files.
    """

    @staticmethod
    @lru_cache(maxsize=None)
    def load(collection_path: str, registry_name: str) -> dict:
        """
        Load a named YAML registry file.

        Args:
            collection_path: Root path of the collection (cisco/nac_dc_vxlan/)
            registry_name:   Name of the registry file (without .yml extension)

        Returns:
            Parsed YAML content as a dict.

        Example:
            resource_types = RegistryLoader.load('/path/to/collection', 'resource_types')
        """
        registry_path = os.path.join(collection_path, 'objects', f'{registry_name}.yml')
        with open(registry_path, 'r') as f:
            return yaml.safe_load(f)
```

---

### Plugin 1: `build_resource_data` — The Resource Builder

**Replaces:** The entire `dtc/common` role's `sub_main_*.yml` and ~20 task files in `tasks/common/` and `tasks/vxlan/`

**Design:**

```python
# plugins/action/dtc/build_resource_data.py

import yaml
from ..plugin_utils.registry_loader import RegistryLoader

class ResourceBuilder:
    """
    Consolidates the Template→Render→Diff→Flag cycle for all resource types.

    Replaces ~1000 lines of repetitive YAML with a data-driven pipeline.

    [v2] Resource type definitions are loaded from an external YAML registry:
        objects/resource_types.yml

    This keeps configuration data separate from logic, making it easy to
    add new resource types by editing YAML alone — no Python changes needed.
    """

    def __init__(self, fabric_type, fabric_name, data_model, role_path,
                 check_roles, force_run_all, run_map_diff_run,
                 collection_path):
        self.fabric_type = fabric_type
        self.fabric_name = fabric_name
        self.data_model = data_model
        self.role_path = role_path
        self.check_roles = check_roles
        self.force_run_all = force_run_all
        self.run_map_diff_run = run_map_diff_run
        self.change_flags = ChangeDetectionManager(...)

        # [v2] Load resource type registry from external YAML
        registry = RegistryLoader.load(collection_path, 'resource_types')
        self.resource_types = registry.get('resource_types', {})

    def build_all(self) -> dict:
        """
        Build all resource data for the given fabric type.
        Returns a dict of {resource_name: rendered_data} plus change flags.
        """
        results = {}
        applicable_resources = [
            (name, cfg) for name, cfg in self.resource_types.items()
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
        # [v2] This could also come from fabric_types.yml via FabricTypeRegistry
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
- **~1000 lines of YAML → ~150 lines of Python** (generic pipeline logic only, no data constants)
- **[v2]** Adding a new resource type = adding 6-8 lines to `objects/resource_types.yml` — no Python changes
- Jinja2 rendering remains (templates are still external), but the orchestration around it is pure Python
- Change detection logic is centralized, not scattered across task files

---

### Plugin 2: `manage_resources` — The Resource Creator

**Replaces:** The `dtc/create` role's `sub_main_*.yml` files and task files in `tasks/common/` and `tasks/common_vxlan/`

**Design:**

```python
# plugins/action/dtc/manage_resources.py

from ..plugin_utils.registry_loader import RegistryLoader

class ResourceManager:
    """
    Manages the ordered creation of NDFC resources for any fabric type.

    Replaces the create role's per-fabric-type sub_main files and
    the conditional cisco.dcnm module calls.

    [v2] Pipeline definitions are loaded from objects/create_pipelines.yml
    """

    def __init__(self, collection_path):
        # [v2] Load pipeline registry from external YAML
        registry = RegistryLoader.load(collection_path, 'create_pipelines')
        self.pipelines = registry.get('create_pipelines', {})

    def create(self, fabric_type, resource_data, change_flags, data_model):
        """Execute the ordered creation pipeline for the given fabric type."""
        pipeline = self.pipelines[fabric_type]

        for step in pipeline:
            resource_name = step['resource_name']
            module = step['module']
            state = step['state']
            flag_name = step['change_flag_guard']

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

from ..plugin_utils.registry_loader import RegistryLoader

class ResourceRemover:
    """
    Manages the ordered removal of unmanaged NDFC resources.

    Removal order is the reverse of creation to respect dependencies
    (e.g., remove networks before VRFs, remove interfaces before switches).

    [v2] Pipeline definitions are loaded from objects/remove_pipelines.yml
    """

    def __init__(self, collection_path):
        # [v2] Load pipeline registry from external YAML
        registry = RegistryLoader.load(collection_path, 'remove_pipelines')
        self.pipelines = registry.get('remove_pipelines', {})

    def remove(self, fabric_type, resource_data, change_flags, data_model,
               run_map_diff_run, force_run_all, interface_delete_mode):
        """Execute the ordered removal pipeline for the given fabric type."""
        pipeline = self.pipelines[fabric_type]

        for step in pipeline:
            resource_name = step['resource_name']
            module = step['module']
            state = step['state']
            flag_name = step['change_flag_guard']

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

from .registry_loader import RegistryLoader

class FabricTypeRegistry:
    """
    Eliminates the repeated when: fabric_type == 'X' patterns.
    Maps fabric types to their namespace variables, templates, and behaviors.

    [v2] Registry data is loaded from objects/fabric_types.yml
    """

    _registry = None

    @classmethod
    def _ensure_loaded(cls, collection_path: str):
        """Load the fabric type registry from YAML if not already loaded."""
        if cls._registry is None:
            data = RegistryLoader.load(collection_path, 'fabric_types')
            cls._registry = data.get('fabric_types', {})

    @classmethod
    def get(cls, fabric_type: str, collection_path: str) -> dict:
        """Get the full config for a fabric type."""
        cls._ensure_loaded(collection_path)
        if fabric_type not in cls._registry:
            raise ValueError(f"Unknown fabric type: {fabric_type}")
        return cls._registry[fabric_type]

    @classmethod
    def resolve_namespace(cls, fabric_type: str, all_vars: dict,
                          collection_path: str) -> dict:
        """
        Replace the 5-way when/set_fact pattern with a single lookup.

        Before (YAML):
            - set_fact: vars_common_local = vars_common_vxlan
              when: type == "VXLAN_EVPN"
            - set_fact: vars_common_local = vars_common_ebgp_vxlan
              when: type == "eBGP_VXLAN"
            ... (5 more)

        After (Python):
            vars_common_local = FabricTypeRegistry.resolve_namespace(
                fabric_type, task_vars, collection_path
            )
        """
        cls._ensure_loaded(collection_path)
        ns = cls._registry[fabric_type]['namespace']
        return all_vars[ns]

    @classmethod
    def supports_feature(cls, fabric_type: str, feature: str,
                         collection_path: str) -> bool:
        """Check if a fabric type supports a specific feature."""
        cls._ensure_loaded(collection_path)
        config = cls._registry.get(fabric_type, {})
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
| **Phase 1** | `RegistryLoader` + `FabricTypeRegistry` + YAML files + refactor fabric-type dispatch | Low — no behavior change | Small |
| **Phase 2** | `build_resource_data` — consolidate the Template→Diff→Flag cycle | Medium — need to ensure Jinja2 rendering context matches | Large |
| **Phase 3** | `manage_resources` — consolidate create operations | Medium — need to preserve `_execute_module` call patterns | Medium |
| **Phase 4** | `remove_resources` — consolidate remove operations | Medium — reverse-order dependencies | Medium |
| **Phase 5** | Deprecate old role task files, update tests | Low | Small |

### Phase 1: RegistryLoader + FabricTypeRegistry (Low Risk)

- **[v2]** Create all YAML registry files under `objects/`:
  - `objects/resource_types.yml`
  - `objects/create_pipelines.yml`
  - `objects/remove_pipelines.yml`
  - `objects/fabric_types.yml`
- **[v2]** Create `plugins/plugin_utils/registry_loader.py`
- Create `plugins/plugin_utils/fabric_type_registry.py` (loads from YAML)
- Refactor existing action plugins to use the registry for namespace resolution
- No changes to role YAML files
- Validates the pattern before broader adoption

### Phase 2: build_resource_data (Core Change)

- Create `plugins/action/dtc/build_resource_data.py`
- **[v2]** Plugin loads `objects/resource_types.yml` via `RegistryLoader`
- Absorb `diff_compare.py` and `diff_model_changes.py` logic into the builder
- Absorb `change_flag_manager.py` into in-memory flag management
- Replace all `common/tasks/common/*.yml` and `common/tasks/vxlan/*.yml` with a single plugin call
- **Critical consideration:** Jinja2 template rendering currently uses Ansible's `template` module which provides access to all `task_vars`. The Python plugin will need to replicate this context when calling `self._templar.template()` or use `self._execute_module()` to delegate to the template module.

### Phase 3: manage_resources (Create)

- Create `plugins/action/dtc/manage_resources.py`
- **[v2]** Plugin loads `objects/create_pipelines.yml` via `RegistryLoader`
- Replaces all `create/tasks/sub_main_*.yml` files
- Replaces `create/tasks/common/*.yml` task files
- Pipeline-driven execution based on fabric type

### Phase 4: remove_resources (Remove)

- Create `plugins/action/dtc/remove_resources.py`
- **[v2]** Plugin loads `objects/remove_pipelines.yml` via `RegistryLoader`
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

7. **[v2] Data-driven registries live in YAML, not Python** — All constants (`RESOURCE_TYPES`, `CREATE_PIPELINES`, `REMOVE_PIPELINES`, `REGISTRY`) are externalized to YAML files under `objects/`. Python plugins are pure execution logic. Adding a new resource type, fabric type, or pipeline step is a YAML-only change — no code modifications, no pull requests touching Python files.

---

## Impact Summary

| Metric | Before | After (v1) | After (v2) |
|--------|--------|------------|------------|
| YAML task files in `dtc/` roles | ~50 files | ~5 files (thin wrappers) | ~5 files (thin wrappers) |
| Lines of repetitive YAML | ~2500+ | ~100 | ~100 |
| Python action plugins | 18 (dtc) + 8 (common) | 21 (dtc) + 8 (common) | 21 (dtc) + 8 (common) + 1 (registry_loader) |
| Fabric-type dispatch blocks | ~30 (scattered across YAML) | 1 (FabricTypeRegistry) | 1 (FabricTypeRegistry, data in YAML) |
| Data constants in Python | — | ~200 lines of dicts | 0 (all in YAML) |
| YAML registry files | 0 | 0 | 4 files under `objects/` |
| Adding a new resource type | Copy 50 lines YAML + edit 3-4 files | Add 6-8 lines to Python dict | Add 6-8 lines to `objects/resource_types.yml` |
| Adding a new fabric type | Edit 10+ sub_main files | Add entry to Python dicts in 3 files | Add entry to YAML files — no Python changes |

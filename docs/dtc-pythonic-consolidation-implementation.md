# DTC Pythonic Consolidation — Implementation Reference

> This document describes the files created as part of the v2 Pythonic consolidation
> of the DTC roles. It covers the YAML registry files, the action plugins, the
> simplified role task files, and the utility module that ties them together.
>
> For the original analysis and design rationale, see:
> - `dtc-pythonic-consolidation-design.md` — Original v1 design document
> - `dtc-pythonic-consolidation-design-v2.md` — Updated v2 design with YAML externalization

---

## Table of Contents

1. [Overview](#overview)
2. [File Inventory](#file-inventory)
3. [Architecture](#architecture)
4. [YAML Registry Files](#yaml-registry-files)
5. [Plugin Utility: RegistryLoader](#plugin-utility-registryloader)
6. [Action Plugin: build_resource_data](#action-plugin-build_resource_data)
7. [Action Plugin: manage_resources](#action-plugin-manage_resources)
8. [Action Plugin: remove_resources](#action-plugin-remove_resources)
9. [Simplified Role Task Files](#simplified-role-task-files)
10. [Data Flow](#data-flow)
11. [Adding New Resources](#adding-new-resources)
12. [Migration Notes](#migration-notes)

---

## Overview

The DTC (Direct-to-Controller) roles in the `cisco.nac_dc_vxlan` collection manage
NDFC fabric lifecycle operations across 5 roles: `common`, `connectivity_check`,
`create`, `deploy`, and `remove`.

The original implementation used extensive YAML task files with per-fabric-type
dispatch (`sub_main_*.yml`) and repetitive template→diff→flag patterns. The v2
consolidation replaces this with:

- **4 YAML registry files** containing all data-driven configuration
- **3 action plugins** implementing the consolidated logic
- **1 utility module** for loading YAML registries
- **3 simplified role task files** (`main_v2.yml`) that are thin wrappers

### Quantitative Impact

| Metric | Before (v1) | After (v2) |
|--------|-------------|------------|
| YAML task files in dtc/ roles | ~50 files | 3 files (`main_v2.yml`) |
| Lines of repetitive YAML | ~2500+ | ~90 |
| Python action plugins | 18 (dtc) + 8 (common) | +3 new + 1 utility |
| YAML registry files | 0 | 4 files under `objects/` |
| Fabric-type dispatch blocks | ~30 (scattered) | 0 (data-driven) |
| Adding a new resource type | Edit 3-4 YAML + Python files | Edit 1 YAML file |

---

## File Inventory

All paths are relative to the collection root:
`vxlan-as-code/collections/ansible_collections/cisco/nac_dc_vxlan/`

### YAML Registries (`objects/`)

| File | Purpose |
|------|---------|
| `objects/resource_types.yml` | Template→Render→Diff→Flag pipeline config per resource type (25 entries) |
| `objects/create_pipelines.yml` | Ordered creation operations per fabric type (6 pipelines) |
| `objects/remove_pipelines.yml` | Ordered removal operations per fabric type (6 pipelines, reverse order) |
| `objects/fabric_types.yml` | Fabric-type namespace, features, and directory mappings (6 types) |

### Action Plugins (`plugins/action/dtc/`)

| File | Class | Replaces |
|------|-------|----------|
| `build_resource_data.py` | `ResourceBuilder` + `ActionModule` | `dtc/common` role — ~25 task files |
| `manage_resources.py` | `ResourceManager` + `ActionModule` | `dtc/create` role — ~18 task files |
| `remove_resources.py` | `ResourceRemover` + `ActionModule` | `dtc/remove` role — ~16 task files |

### Plugin Utility (`plugins/plugin_utils/`)

| File | Class | Purpose |
|------|-------|---------|
| `registry_loader.py` | `RegistryLoader` | Shared YAML loader with `lru_cache` and collection path auto-discovery |

### Simplified Role Tasks (`roles/dtc/*/tasks/`)

| File | Tasks | Replaces |
|------|-------|----------|
| `common/tasks/main_v2.yml` | 4 tasks | `main.yml` + 6 `sub_main_*.yml` + ~25 task files |
| `create/tasks/main_v2.yml` | 2 tasks | `main.yml` + 6 `sub_main_*.yml` + ~12 task files |
| `remove/tasks/main_v2.yml` | 3 tasks | `main.yml` + 6 `sub_main_*.yml` + ~10 task files + inline deploy |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Ansible Playbook                            │
│  roles: common → connectivity_check → create → deploy → remove │
└──────┬───────────────────────┬─────────────────────┬────────────┘
       │                       │                     │
       ▼                       ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ main_v2.yml  │      │ main_v2.yml  │      │ main_v2.yml  │
│   (common)   │      │   (create)   │      │   (remove)   │
└──────┬───────┘      └──────┬───────┘      └──────┬───────┘
       │                     │                     │
       ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ build_       │      │ manage_      │      │ remove_      │
│ resource_    │      │ resources.py │      │ resources.py │
│ data.py      │      │              │      │              │
└──────┬───────┘      └──────┬───────┘      └──────┬───────┘
       │                     │                     │
       ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    RegistryLoader                           │
│              (plugins/plugin_utils/registry_loader.py)      │
└──────┬───────────────┬────────────────┬────────────┬────────┘
       │               │                │            │
       ▼               ▼                ▼            ▼
┌──────────┐   ┌──────────────┐  ┌──────────┐  ┌──────────┐
│ resource │   │   create_    │  │  remove_  │  │ fabric_  │
│ _types   │   │  pipelines   │  │ pipelines │  │  types   │
│  .yml    │   │    .yml      │  │   .yml    │  │   .yml   │
└──────────┘   └──────────────┘  └──────────┘  └──────────┘
```

---

## YAML Registry Files

### `objects/resource_types.yml`

Consumed by `build_resource_data.py`. Defines the Template→Render→Diff→Flag pipeline
for each of the 25 NDFC resource types.

**Entry structure:**

```yaml
resource_types:
  fabric:                            # Logical resource name
    template: ndfc_fabric.j2         # Jinja2 template file
    output_file: ndfc_fabric.yml     # Rendered output filename
    change_flag: changes_detected_fabric  # Flag to set on change (null = none)
    diff_compare: false              # Whether structural diff is needed
    fabric_types:                    # Which fabric types this applies to
      - VXLAN_EVPN
      - eBGP_VXLAN
      - ISN
      - MSD
      - MCFG
      - External
    pre_hooks:                       # (optional) Hooks before rendering
      - get_poap_data
    post_hooks:                      # (optional) Hooks after rendering
      - get_credentials
```

**Categories (25 resource types):**
- Fabric & Inventory: `fabric`, `inventory`, `inventory_no_bootstrap`
- VPC: `vpc_domain_id_resource`, `vpc_fabric_peering_links`, `vpc_peering_pairs`
- Overlay: `vrfs`, `networks`
- Interfaces: `interface_breakout`, `interface_breakout_preprov`, `interface_trunk`,
  `interface_routed`, `sub_interface_routed`, `interface_access`, `interface_trunk_po`,
  `interface_access_po`, `interface_po_routed`, `interface_loopback`, `interface_dot1q`,
  `interface_vpc`
- Policies/Links: `policy`, `fabric_links`, `edge_connections`, `underlay_ip_address`
- MSD-specific: `bgw_anycast_vip`

### `objects/create_pipelines.yml`

Consumed by `manage_resources.py`. Defines the ordered pipeline of creation operations
for each of the 6 supported fabric types.

**Entry structure:**

```yaml
create_pipelines:
  VXLAN_EVPN:
    - resource_name: fabric              # Which resource data to pass
      module: dcnm_fabric                # cisco.dcnm module (prefix added at runtime)
      state: merged                      # Module state parameter
      change_flag_guard: changes_detected_fabric  # Guard — skip if False
```

**Internal methods** (prefixed with `_`) call Python methods instead of NDFC modules:
- `_config_save` — POST to `/config-save` endpoint
- `_vrfs_networks_pipeline` — Ordered VRF→Network creation sub-pipeline
- `_prepare_msite_data` — Multi-site data preparation for MSD/MCFG

### `objects/remove_pipelines.yml`

Consumed by `remove_resources.py`. Same structure as create_pipelines but with
**reverse dependency ordering** and `deleted`/`overridden` states.

Example: For VXLAN_EVPN, the removal order is:
1. edge_connections → 2. policies → 3. interfaces → 4. networks →
5. vrfs → 6. links → 7. vpc_peers → 8. switches

### `objects/fabric_types.yml`

Maps each fabric type to its namespace, directory, and feature capabilities:

```yaml
fabric_types:
  VXLAN_EVPN:
    namespace: vars_common_vxlan       # Ansible variable namespace
    file_subdir: vxlan                 # Output subdirectory under files/
    global_key: ibgp                   # Key into global config
    fabric_template_dir: dc_vxlan_fabric
    supports_overlay: true
    supports_vpc: true
    supports_multisite: false
```

---

## Plugin Utility: RegistryLoader

**File:** `plugins/plugin_utils/registry_loader.py`

Shared utility for loading and caching YAML registry files. Used by all three
action plugins to load their configuration from `objects/`.

### Key Features

- **`lru_cache`**: Registry files are loaded once and cached for the duration of
  the Ansible run. Subsequent calls return the cached result.
- **`get_collection_path()`**: Auto-derives the collection root from `__file__`
  location (3 directories up from `plugins/plugin_utils/`), eliminating the need
  to pass the collection path as a parameter.
- **`clear_cache()`**: Clears the LRU cache — useful in testing.

### Usage

```python
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.registry_loader import RegistryLoader

# Auto-discover collection path
collection_path = RegistryLoader.get_collection_path()

# Load a registry (cached after first call)
resource_types = RegistryLoader.load(collection_path, 'resource_types')
pipelines = RegistryLoader.load(collection_path, 'create_pipelines')
```

---

## Action Plugin: build_resource_data

**File:** `plugins/action/dtc/build_resource_data.py`
**Replaces:** `dtc/common` role — 6 `sub_main_*.yml` + ~25 task files (~1000 lines YAML)

### Purpose

Consolidates the Template→Render→Diff→Flag cycle for all resource types into a
single action plugin. For each resource type applicable to the current fabric type,
it executes:

1. Backup previous rendered file to `.old`
2. Render Jinja2 template → YAML output file (via `ansible.builtin.template`)
3. Load rendered data into memory
4. MD5 diff check with `__omit_place_holder__` normalization
5. Structural diff via `cisco.nac_dc_vxlan.dtc.diff_compare` (if enabled)
6. Update the change detection flag
7. Cleanup `.old` backup

### Classes

| Class | Purpose |
|-------|---------|
| `ResourceBuilder` | Core pipeline logic — template rendering, diff, flag management |
| `ActionModule` | Ansible `ActionBase` wrapper — parameter validation, error handling |

### Parameters (task args)

| Parameter | Required | Description |
|-----------|----------|-------------|
| `fabric_type` | Yes | `VXLAN_EVPN`, `eBGP_VXLAN`, `ISN`, `MSD`, `MCFG`, `External` |
| `fabric_name` | Yes | Name of the NDFC fabric |
| `data_model` | Yes | Extended data model (`data_model_extended`) |
| `role_path` | Yes | Path to the common role (for template/file resolution) |
| `check_roles` | Yes | Check roles configuration |
| `force_run_all` | No | Force full run regardless of diff state (default: `false`) |
| `run_map_diff_run` | No | Whether diff-based run is active (default: `true`) |

### Return Values

```yaml
resource_data:                    # Dict of resource results
  fabric:
    data: [...]                   # Rendered resource data (list)
    changed: true                 # Whether this resource changed
    diff:                         # Structural diff result (if diff_compare enabled)
      updated: [...]
      removed: [...]
      equal: [...]
  inventory:
    data: [...]
    changed: false
    diff: null
  # ... (all applicable resource types)
  interface_all:                  # Composite of all interface types
    data_create: [...]
    data_remove_overridden: [...]
    changed: true
    diff: { updated: [...], removed: [...], equal: [...] }

change_flags:                     # Change detection state
  changes_detected_fabric: true
  changes_detected_inventory: false
  changes_detected_interfaces: true
  # ... (all flags)
  changes_detected_any: true      # Aggregate — true if any flag is true
```

### Key Implementation Details

- **Template rendering** delegates to `ansible.builtin.template` via `_execute_module`
  to preserve the full Jinja2 context (task_vars, filters, lookups)
- **MD5 normalization** replicates the exact regex from `diff_model_changes.py`:
  `r'__omit_place_holder__\S+'` → `'NORMALIZED'`
- **Structural diff** delegates to the existing `diff_compare` action plugin
- **Interface compositing**: `_build_interface_all()` aggregates 12 interface types
  into a single list for create/remove operations

---

## Action Plugin: manage_resources

**File:** `plugins/action/dtc/manage_resources.py`
**Replaces:** `dtc/create` role — 6 `sub_main_*.yml` + ~12 task files

### Purpose

Executes the ordered creation pipeline for any fabric type. Iterates through the
pipeline steps from `create_pipelines.yml`, checking change flag guards and data
availability before calling the appropriate `cisco.dcnm` module.

### Classes

| Class | Purpose |
|-------|---------|
| `ResourceManager` | Pipeline execution, NDFC module calls, internal methods |
| `ActionModule` | Ansible `ActionBase` wrapper |

### Parameters (task args)

| Parameter | Required | Description |
|-----------|----------|-------------|
| `fabric_type` | Yes | Fabric type |
| `fabric_name` | Yes | Fabric name |
| `data_model` | Yes | Extended data model |
| `resource_data` | Yes | Resource data from `build_resource_data` (`vars_common`) |
| `change_flags` | Yes | Change flags from `build_resource_data` |
| `nd_version` | No | Nexus Dashboard version string |

### Pipeline Execution Logic

For each step in the pipeline:

1. **Check `change_flag_guard`** — skip step if the guard flag is `False`
2. **Resolve data** — get resource data; prefer `diff.updated` for diff-based runs
3. **Route by module type:**
   - `_`-prefixed → call internal Python method (e.g., `_config_save`)
   - Otherwise → call `cisco.dcnm.{module}` via `_execute_module`
4. **Fail fast** — if any NDFC module call fails, the pipeline stops and returns the error

### Internal Methods

| Method | Purpose |
|--------|---------|
| `_config_save` | POST to NDFC config-save endpoint. Treats HTTP 500 as non-fatal (matches existing rescue block) |
| `_vrfs_networks_pipeline` | Creates VRFs first, then Networks (dependency ordering) |
| `_prepare_msite_data` | Delegates to `cisco.nac_dc_vxlan.dtc.prepare_msite_data` for MSD/MCFG |

---

## Action Plugin: remove_resources

**File:** `plugins/action/dtc/remove_resources.py`
**Replaces:** `dtc/remove` role — 6 `sub_main_*.yml` + ~10 task files

### Purpose

Executes the ordered removal pipeline for any fabric type. Removal order is the
**reverse of creation** to respect dependencies. Includes special handling for
interface removal modes.

### Classes

| Class | Purpose |
|-------|---------|
| `ResourceRemover` | Pipeline execution, interface removal modes, NDFC calls |
| `ActionModule` | Ansible `ActionBase` wrapper |

### Parameters (task args)

| Parameter | Required | Description |
|-----------|----------|-------------|
| `fabric_type` | Yes | Fabric type |
| `fabric_name` | Yes | Fabric name |
| `data_model` | Yes | Extended data model |
| `resource_data` | Yes | Resource data from `build_resource_data` |
| `change_flags` | Yes | Change flags from `build_resource_data` |
| `run_map_diff_run` | No | Whether diff-based run is active (default: `true`) |
| `force_run_all` | No | Force full run (default: `false`) |
| `interface_delete_mode` | No | Enable interface deletion (default: `false`) |
| `stage_remove` | No | Stage removals without deploying (default: `false`) |

### Interface Removal Modes

The `_handle_interface_removal()` method implements two modes:

| Mode | Condition | State | Data Source |
|------|-----------|-------|-------------|
| Diff Run | `diff_run=True`, `force_run_all=False` | `deleted` | `diff.removed` — only removed interfaces |
| Full Run | `diff_run=False` or `force_run_all=True` | `overridden` | `data_remove_overridden` — enforce data model |

All interface removal calls use `deploy: false` — deployment is handled separately
by the `fabric_deploy_manager` in the role task file.

### Removal Data Resolution

`_get_removal_data()` determines what data to use for each removal step:
1. If diff-run is active → use `diff.removed` list
2. Otherwise → use full resource `data` list

---

## Simplified Role Task Files

### `common/tasks/main_v2.yml` (4 tasks)

```yaml
# 1. Store role_path for template resolution
- name: Create Fact To Store Common Role Path
  ansible.builtin.set_fact:
    common_role_path: "{{ role_path }}"

# 2. Single plugin call replaces ~25 task files
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

# 3. Store results for downstream roles
- name: Store Resource Data and Change Flags
  ansible.builtin.set_fact:
    vars_common: "{{ resource_build_result.resource_data }}"
    change_flags: "{{ resource_build_result.change_flags }}"

# 4. Optional debug output
- name: Display Change Flags
  ansible.builtin.debug:
    var: change_flags
    verbosity: 1
```

### `create/tasks/main_v2.yml` (2 tasks)

```yaml
# 1. Single plugin call replaces ~18 task files
- name: Create Resources in Nexus Dashboard
  cisco.nac_dc_vxlan.dtc.manage_resources:
    fabric_type: "{{ data_model_extended.vxlan.fabric.type }}"
    fabric_name: "{{ data_model_extended.vxlan.fabric.name }}"
    data_model: "{{ data_model_extended }}"
    resource_data: "{{ vars_common }}"
    change_flags: "{{ change_flags }}"
    nd_version: "{{ nd_version }}"
  when: change_flags.changes_detected_any

# 2. Mark stage completed (preserves run_map tracking)
- name: Mark Stage Role Create Completed
  cisco.nac_dc_vxlan.common.run_map:
    data_model: "{{ data_model_extended }}"
    stage: role_create_completed
```

### `remove/tasks/main_v2.yml` (3 tasks)

```yaml
# 1. Single plugin call replaces ~16 task files
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

# 2. Deploy changes (only for non-staged, applicable fabric types)
- name: Deploy Remove Changes
  cisco.nac_dc_vxlan.dtc.fabric_deploy_manager:
    fabric_name: "{{ data_model_extended.vxlan.fabric.name }}"
    fabric_type: "{{ data_model_extended.vxlan.fabric.type }}"
    operation: all
  when:
    - stage_remove is false | bool
    - change_flags.changes_detected_any
    - data_model_extended.vxlan.fabric.type in ['VXLAN_EVPN', 'eBGP_VXLAN', 'ISN', 'External']

# 3. Mark stage completed
- name: Mark Stage Role Remove Completed
  cisco.nac_dc_vxlan.common.run_map:
    data_model: "{{ data_model_extended }}"
    stage: role_remove_completed
```

---

## Data Flow

```
Playbook
  │
  ├─► common role (main_v2.yml)
  │     │
  │     └─► build_resource_data plugin
  │           ├── Loads: objects/resource_types.yml
  │           ├── For each applicable resource:
  │           │     Template → Render → MD5 Diff → Flag → Structural Diff
  │           ├── Composites interface_all from 12 interface types
  │           └── Returns: { resource_data, change_flags }
  │                 │
  │                 ▼
  │           set_fact: vars_common = resource_data
  │           set_fact: change_flags = change_flags
  │
  ├─► create role (main_v2.yml)
  │     │
  │     └─► manage_resources plugin
  │           ├── Loads: objects/create_pipelines.yml
  │           ├── Reads: vars_common, change_flags
  │           ├── For each pipeline step:
  │           │     Check guard → Resolve data → Call cisco.dcnm module
  │           └── Returns: { results[], failed }
  │
  ├─► deploy role (unchanged — fabric_deploy_manager)
  │
  └─► remove role (main_v2.yml)
        │
        ├─► remove_resources plugin
        │     ├── Loads: objects/remove_pipelines.yml
        │     ├── Reads: vars_common, change_flags
        │     ├── Gets switch list from NDFC
        │     ├── For each pipeline step (reverse order):
        │     │     Check guard → Resolve removal data → Call cisco.dcnm module
        │     │     (Special: interface_delete_mode → deleted/overridden)
        │     └── Returns: { results[], failed }
        │
        └─► fabric_deploy_manager (existing — deploys after removal)
```

---

## Adding New Resources

### New Resource Type (e.g., adding `ndfc_freeform_config`)

1. **Create the Jinja2 template** in the role's `templates/` directory:
   ```
   roles/dtc/common/templates/ndfc_freeform_config.j2
   ```

2. **Add entry to `objects/resource_types.yml`:**
   ```yaml
   freeform_config:
     template: ndfc_freeform_config.j2
     output_file: ndfc_freeform_config.yml
     change_flag: changes_detected_freeform_config
     diff_compare: true
     fabric_types:
       - VXLAN_EVPN
       - eBGP_VXLAN
   ```

3. **Add pipeline step to `objects/create_pipelines.yml`:**
   ```yaml
   # Add under VXLAN_EVPN (and other applicable types)
   - resource_name: freeform_config
     module: dcnm_policy
     state: merged
     change_flag_guard: changes_detected_freeform_config
   ```

4. **Add removal step to `objects/remove_pipelines.yml`:**
   ```yaml
   - resource_name: freeform_config
     module: dcnm_policy
     state: deleted
     change_flag_guard: changes_detected_freeform_config
   ```

**No Python changes required.**

### New Fabric Type

1. Add to `objects/fabric_types.yml`
2. Add pipeline to `objects/create_pipelines.yml`
3. Add pipeline to `objects/remove_pipelines.yml`
4. Add applicable entries in `objects/resource_types.yml` `fabric_types` lists

---

## Migration Notes

### Activation

To switch from v1 to v2, rename the task files in each role:

```bash
# For each role (common, create, remove):
cd roles/dtc/{role}/tasks/
mv main.yml main_v1.yml      # Preserve original
mv main_v2.yml main.yml      # Activate v2
```

### Rollback

```bash
cd roles/dtc/{role}/tasks/
mv main.yml main_v2.yml      # Deactivate v2
mv main_v1.yml main.yml      # Restore original
```

### Preserved Behaviors

The v2 implementation preserves these behaviors from v1:

- **Tags**: `nac_tags.common_role`, `nac_tags.create`, `nac_tags.remove`
- **`delegate_to: localhost`**: Where the originals used it
- **`change_flags.changes_detected_any`**: Gating on create and remove roles
- **`run_map` stage markers**: `role_create_completed`, `role_remove_completed`
- **`stage_remove` logic**: Non-staged removals trigger deploy for applicable fabric types
- **Deploy exclusions**: MSD and MCFG fabrics are excluded from post-remove deploy
- **`__omit_place_holder__` normalization**: Same regex pattern as `diff_model_changes.py`
- **Interface removal ordering**: Same diff-run vs full-run conditional logic
- **Config-save error handling**: HTTP 500 treated as non-fatal (matching rescue blocks)

### Dependencies

The v2 plugins depend on:
- `cisco.dcnm` collection modules (`dcnm_fabric`, `dcnm_inventory`, etc.)
- Existing collection plugins: `diff_compare`, `prepare_msite_data`, `fabric_deploy_manager`
- Existing collection utilities: `change_flag_manager`, `run_map`
- Python stdlib: `yaml`, `hashlib`, `shutil`, `re`, `os`, `functools.lru_cache`

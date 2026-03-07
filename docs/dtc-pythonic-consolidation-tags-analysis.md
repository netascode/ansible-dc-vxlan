# DTC Pythonic Consolidation — Ansible Tags Analysis

> **Date:** March 6, 2026
> **Scope:** Analysis of how Ansible tags are currently used in `nac_dc_vxlan`, the problem created by consolidating many YAML tasks into single action plugin calls, and the recommended Pythonic approach to preserve tag-based selective execution.

---

## Table of Contents

1. [Current Tag Architecture](#1-current-tag-architecture)
2. [The Problem: Tag Granularity Lost in Consolidation](#2-the-problem-tag-granularity-lost-in-consolidation)
3. [Approach Evaluation](#3-approach-evaluation)
4. [Recommended Approach: Hybrid — YAML Registry + Python Tag Filtering](#4-recommended-approach-hybrid--yaml-registry--python-tag-filtering)
5. [Implementation Design](#5-implementation-design)
6. [Updated File Inventory](#6-updated-file-inventory)
7. [Migration Considerations](#7-migration-considerations)

---

## 1. Current Tag Architecture

### Tag Definitions

Tags are defined in `roles/common_global/vars/main.yml` under the `nac_tags` dict. This is a centralized tag registry consumed by all DTC roles via Jinja2 variable expansion.

**Structure:**

```yaml
nac_tags:
  # Role-level aggregate tags (applied to entire role entry points)
  all:           [cc_verify, 8× cr_manage_*, 8× rr_manage_*, role_validate, role_create, role_deploy, role_remove]
  common_role:   [role_create, role_deploy, role_remove, 8× cr_manage_*, 8× rr_manage_*]
  validate_role: [role_validate, role_create, role_deploy, role_remove, 8× cr_manage_*, 8× rr_manage_*]
  connectivity_check: [cc_verify, role_create, role_deploy, role_remove, 8× cr_manage_*, 8× rr_manage_*]
  deploy:        [role_deploy]

  # Create — aggregate and per-resource
  create:              [cr_manage_fabric, cr_manage_switches, cr_manage_vpc_peers, cr_manage_interfaces, cr_manage_vrfs_networks, cr_manage_policy, cr_manage_links, cr_manage_edge_connections]
  create_fabric:       [cr_manage_fabric]
  create_switches:     [cr_manage_switches]
  create_vpc_peers:    [cr_manage_vpc_peers]
  create_interfaces:   [cr_manage_interfaces]
  create_vrfs_networks:[cr_manage_vrfs_networks]
  create_policy:       [cr_manage_policy]
  create_links:        [cr_manage_links]
  create_edge_connections: [cr_manage_edge_connections]

  # Remove — aggregate and per-resource
  remove:              [rr_manage_interfaces, rr_manage_networks, rr_manage_vrfs, rr_manage_vpc_peers, rr_manage_links, rr_manage_switches, rr_manage_policy, rr_manage_edge_connections]
  remove_interfaces:   [rr_manage_interfaces]
  remove_networks:     [rr_manage_networks]
  remove_vrfs:         [rr_manage_vrfs]
  remove_vpc_peers:    [rr_manage_vpc_peers]
  remove_links:        [rr_manage_links]
  remove_switches:     [rr_manage_switches]
  remove_policy:       [rr_manage_policy]
  remove_edge_connections: [rr_manage_edge_connections]
```

### Tag Validation

The `verify_tags` action plugin (called from `common_global/tasks/main.yml`) validates that every user-supplied `--tags` value exists in `nac_tags.all`. If an unknown tag is passed, the play fails immediately with a descriptive error.

### How Tags Are Applied Today

Each `sub_main_*.yml` file applies **per-resource granular tags** to individual `import_tasks` blocks:

```yaml
# roles/dtc/create/tasks/sub_main_vxlan.yml (simplified)

- name: Create Fabric
  import_tasks: common/fabric.yml
  when: change_flags.changes_detected_fabric
  tags: "{{ nac_tags.create_fabric }}"          # → [cr_manage_fabric]

- name: Manage Switches
  import_tasks: common/devices.yml
  when: change_flags.changes_detected_inventory
  tags: "{{ nac_tags.create_switches }}"        # → [cr_manage_switches]

- name: Manage Interfaces
  import_tasks: common/interfaces.yml
  when: change_flags.changes_detected_interfaces
  tags: "{{ nac_tags.create_interfaces }}"      # → [cr_manage_interfaces]

- name: Manage VRFs and Networks
  import_tasks: common_vxlan/vrfs_networks.yml
  when: change_flags.changes_detected_vrfs
  tags: "{{ nac_tags.create_vrfs_networks }}"   # → [cr_manage_vrfs_networks]
```

This enables operators to run targeted subsets of a role:

```bash
# Only create fabric and switches — skip everything else
ansible-playbook vxlan.yaml --tags cr_manage_fabric,cr_manage_switches

# Only remove interfaces
ansible-playbook vxlan.yaml --tags rr_manage_interfaces
```

### Tag-to-Resource Mapping (Current)

| Ansible Tag | Create Resource | Remove Resource |
|-------------|-----------------|-----------------|
| `cr_manage_fabric` | `fabric` | — |
| `cr_manage_switches` | `devices` | — |
| `cr_manage_vpc_peers` | `vpc_peering`, `config_save` | — |
| `cr_manage_interfaces` | `interfaces` | — |
| `cr_manage_vrfs_networks` | `vrfs_networks` (VRFs + Networks) | — |
| `cr_manage_policy` | `policies` | — |
| `cr_manage_links` | `links`, `edge_connections` | — |
| `cr_manage_edge_connections` | `edge_connections` | — |
| `rr_manage_edge_connections` | — | `edge_connections` |
| `rr_manage_policy` | — | `policies` |
| `rr_manage_interfaces` | — | `interfaces` |
| `rr_manage_networks` | — | `networks` |
| `rr_manage_vrfs` | — | `vrfs` |
| `rr_manage_links` | — | `links` |
| `rr_manage_vpc_peers` | — | `vpc_peers` |
| `rr_manage_switches` | — | `switches` |

---

## 2. The Problem: Tag Granularity Lost in Consolidation

### Current v2 Design

The v2 `main_v2.yml` files consolidate all per-resource tasks into a **single action plugin call**:

```yaml
# roles/dtc/create/tasks/main_v2.yml
- name: Create Resources in Nexus Dashboard
  cisco.nac_dc_vxlan.dtc.manage_resources:
    fabric_type: "{{ data_model_extended.vxlan.fabric.type }}"
    ...
  tags: "{{ nac_tags.create }}"    # ← ALL 8 create tags applied to ONE task
```

```yaml
# roles/dtc/remove/tasks/main_v2.yml
- name: Remove Unmanaged Resources from Nexus Dashboard
  cisco.nac_dc_vxlan.dtc.remove_resources:
    fabric_type: "{{ data_model_extended.vxlan.fabric.type }}"
    ...
  tags: "{{ nac_tags.remove }}"    # ← ALL 8 remove tags applied to ONE task
```

### The Problem

Because all 8 `cr_manage_*` tags are applied to the single `manage_resources` task, **any matching tag triggers the entire pipeline**:

```bash
# INTENDED: Only create fabric
ansible-playbook vxlan.yaml --tags cr_manage_fabric

# ACTUAL (v2): manage_resources runs the FULL create pipeline
# because the task matches cr_manage_fabric (it has ALL create tags)
# and the Python plugin has no knowledge of which tag was selected
```

The v2 design preserves tag **activation** (the task runs when any matching tag is passed) but loses tag **selectivity** (the ability to run only specific resource operations within the pipeline).

### Why This Matters

Operators use targeted tags for:
- **Debugging:** Run only the failing resource step to isolate issues
- **Performance:** Skip expensive operations (e.g., VRF/Network creation) when only changing interfaces
- **Safety:** Apply changes incrementally rather than running the full pipeline
- **Recovery:** Re-run a specific step after a partial failure without repeating earlier steps

---

## 3. Approach Evaluation

### Approach A: Tags in YAML Pipeline Files Only

Add a `tag` field to each pipeline step in `create_pipelines.yml` / `remove_pipelines.yml`. The Python plugin receives `ansible_run_tags` and skips steps whose tags don't match.

**Pros:**
- Tags stay in YAML (data-driven, consistent with OCP design)
- No Python code changes needed to add/modify tags
- Tags live alongside the pipeline steps they control

**Cons:**
- Python must replicate Ansible's tag matching logic (including `all` special tag)
- Tag definitions split across two locations (`common_global/vars/main.yml` for validation AND pipeline YAML for filtering)
- The `--list-tags` Ansible feature won't show per-step tags (they're hidden inside the plugin)

### Approach B: Tags in Python Action Plugins Only

The Python plugin reads `ansible_run_tags` from `task_vars` and maps tag names to resource names internally via a Python dict.

**Pros:**
- Self-contained — filtering logic lives with execution logic

**Cons:**
- Violates OCP — adding a new tag requires modifying Python code
- Duplicates data that already exists in `common_global/vars/main.yml`
- Tag-to-resource mapping is opaque (hidden in code)

### Approach C: Hybrid — YAML Registry + Python Tag Filtering (Recommended)

Add a `tag` field to each pipeline step in the YAML registry files. The Python plugin receives `ansible_run_tags` as a parameter and uses it to filter pipeline steps before execution. The `nac_tags` var in `common_global/vars/main.yml` remains the source of truth for Ansible-level task tags and validation.

**Pros:**
- Tags are data-driven (YAML) — consistent with OCP design
- Tag-to-step mapping is explicit and auditable in the pipeline YAML
- Python filtering logic is generic — 5-10 lines, no resource-specific code
- `nac_tags` in `common_global/vars/main.yml` remains the single source for validation
- Backward-compatible — operators use the same `--tags` CLI they already know

**Cons:**
- Per-step tag granularity is still not visible to `--list-tags` (Ansible limitation — tags inside Python plugins are invisible to Ansible's static tag parser)

### Approach D: Split Plugin Into Per-Resource Tasks

Revert to multiple YAML tasks, each calling a thin per-resource plugin. Each task carries its own Ansible tag natively.

**Cons:**
- Defeats the purpose of the Pythonic consolidation
- Returns to the pattern of 8-10 tasks per role
- Requires maintaining per-resource wrappers

---

## 4. Recommended Approach: Hybrid — YAML Registry + Python Tag Filtering

### Design Principles

1. **Pipeline YAML files own the tag-to-step mapping** — each step declares which Ansible tag controls it
2. **Python plugins receive active tags and filter steps** — generic filtering logic, no tag-specific code
3. **`common_global/vars/main.yml` remains the validation source** — no change to the verify_tags flow
4. **`all` tag = run everything** — matches existing Ansible convention
5. **No active tags = run everything** — when the plugin is called without tag filtering (e.g., the wrapper YAML task matched because it carries all tags), the plugin runs the full pipeline

### Data Flow

```
User: ansible-playbook vxlan.yaml --tags cr_manage_fabric,cr_manage_switches
  │
  ├─ Ansible evaluates task tags: main_v2.yml "Create Resources" task
  │   has tags: {{ nac_tags.create }} = [cr_manage_fabric, ..., cr_manage_policy]
  │   cr_manage_fabric matches → task RUNS
  │
  ├─ ActionModule.run() receives:
  │   task_vars['ansible_run_tags'] = ['cr_manage_fabric', 'cr_manage_switches']
  │
  ├─ Plugin loads create_pipelines.yml with tag fields:
  │   - resource_name: fabric      tag: cr_manage_fabric       ← MATCHES
  │   - resource_name: devices     tag: cr_manage_switches     ← MATCHES
  │   - resource_name: vpc_peering tag: cr_manage_vpc_peers    ← SKIP
  │   - resource_name: interfaces  tag: cr_manage_interfaces   ← SKIP
  │   - ...
  │
  └─ Plugin executes ONLY: fabric, devices
```

---

## 5. Implementation Design

### 5.1 Pipeline YAML Changes

Add a `tag` field to every pipeline step. The tag value is the **atomic tag name** (e.g., `cr_manage_fabric`), not the `nac_tags.*` key.

#### `objects/create_pipelines.yml` — Updated

```yaml
create_pipelines:
  VXLAN_EVPN:
    - resource_name: fabric
      module: dcnm_fabric
      state: merged
      change_flag_guard: changes_detected_fabric
      tag: cr_manage_fabric                          # NEW

    - resource_name: devices
      module: dcnm_inventory
      state: merged
      change_flag_guard: changes_detected_inventory
      tag: cr_manage_switches                        # NEW

    - resource_name: vpc_peering
      module: dcnm_links
      state: merged
      change_flag_guard: changes_detected_vpc_peering
      tag: cr_manage_vpc_peers                       # NEW

    - resource_name: config_save
      module: _config_save
      state: null
      change_flag_guard: changes_detected_vpc_peering
      tag: cr_manage_vpc_peers                       # NEW (same as vpc_peering — coupled operation)

    - resource_name: interfaces
      module: dcnm_interface
      state: replaced
      change_flag_guard: changes_detected_interfaces
      tag: cr_manage_interfaces                      # NEW

    - resource_name: edge_connections
      module: dcnm_links
      state: merged
      change_flag_guard: changes_detected_edge_connections
      tag: cr_manage_edge_connections                # NEW

    - resource_name: vrfs_networks
      module: _vrfs_networks_pipeline
      state: null
      change_flag_guard: changes_detected_vrfs
      tag: cr_manage_vrfs_networks                   # NEW

    - resource_name: links
      module: dcnm_links
      state: merged
      change_flag_guard: changes_detected_fabric_links
      tag: cr_manage_links                           # NEW

    - resource_name: policies
      module: dcnm_policy
      state: merged
      change_flag_guard: changes_detected_policy
      tag: cr_manage_policy                          # NEW
```

#### `objects/remove_pipelines.yml` — Updated

```yaml
remove_pipelines:
  VXLAN_EVPN:
    - resource_name: edge_connections
      module: dcnm_links
      state: deleted
      change_flag_guard: changes_detected_edge_connections
      tag: rr_manage_edge_connections                # NEW

    - resource_name: policies
      module: dcnm_policy
      state: deleted
      change_flag_guard: changes_detected_policy
      tag: rr_manage_policy                          # NEW

    - resource_name: interfaces
      module: dcnm_interface
      state: deleted
      change_flag_guard: changes_detected_interfaces
      tag: rr_manage_interfaces                      # NEW

    - resource_name: networks
      module: dcnm_network
      state: deleted
      change_flag_guard: changes_detected_networks
      tag: rr_manage_networks                        # NEW

    - resource_name: vrfs
      module: dcnm_vrf
      state: deleted
      change_flag_guard: changes_detected_vrfs
      tag: rr_manage_vrfs                            # NEW

    - resource_name: links
      module: dcnm_links
      state: deleted
      change_flag_guard: changes_detected_fabric_links
      tag: rr_manage_links                           # NEW

    - resource_name: vpc_peers
      module: dcnm_links
      state: deleted
      change_flag_guard: changes_detected_vpc_peering
      tag: rr_manage_vpc_peers                       # NEW

    - resource_name: switches
      module: dcnm_inventory
      state: deleted
      change_flag_guard: changes_detected_inventory
      tag: rr_manage_switches                        # NEW
```

The same `tag` field is added to all fabric types (eBGP_VXLAN, ISN, External, MSD, MCFG) using the same atomic tag values.

### 5.2 Python Tag Filtering Logic

A shared utility method provides the tag filtering logic. This is used by both `ResourceManager` and `ResourceRemover`.

#### Option A: Shared Function in `registry_loader.py`

```python
# plugins/plugin_utils/registry_loader.py — add to RegistryLoader class

@staticmethod
def filter_pipeline_by_tags(pipeline, active_tags):
    """
    Filter a pipeline's steps based on active Ansible run tags.

    If 'all' is in active_tags, or active_tags is empty/None, all steps
    are returned (no filtering). Otherwise, only steps whose 'tag' field
    matches one of the active tags are included.

    Args:
        pipeline: List of pipeline step dicts from the YAML registry
        active_tags: List of active Ansible tags (from ansible_run_tags)

    Returns:
        Filtered list of pipeline steps
    """
    # No filtering when 'all' is active or no tags specified
    if not active_tags or 'all' in active_tags:
        return pipeline

    return [
        step for step in pipeline
        if step.get('tag') is None or step.get('tag') in active_tags
    ]
```

**Key behavior:**
- `active_tags = ['all']` → run everything (Ansible convention)
- `active_tags = []` or `None` → run everything (no `--tags` specified)
- `step['tag'] is None` → always runs (infrastructure steps like `_prepare_msite_data` that should never be skipped individually)
- `step['tag'] = 'cr_manage_fabric'` and `'cr_manage_fabric' in active_tags` → runs
- `step['tag'] = 'cr_manage_fabric'` and `'cr_manage_fabric' not in active_tags` → skipped

#### Option B: Standalone Utility (`tag_filter.py`)

If keeping `RegistryLoader` strictly focused on file I/O (SRP), the filter can live in its own utility:

```python
# plugins/plugin_utils/tag_filter.py

class TagFilter:
    """
    Filters pipeline steps based on active Ansible run tags.

    Used by ResourceManager and ResourceRemover to implement
    per-step tag selectivity within a consolidated action plugin.
    """

    @staticmethod
    def filter(pipeline, active_tags):
        """
        Return only pipeline steps matching the active tags.

        Rules:
        - 'all' in active_tags → no filtering (run everything)
        - empty/None active_tags → no filtering
        - step has no 'tag' key → always included
        - step's tag not in active_tags → excluded
        """
        if not active_tags or 'all' in active_tags:
            return pipeline

        return [
            step for step in pipeline
            if step.get('tag') is None or step.get('tag') in active_tags
        ]
```

### 5.3 Plugin Integration

#### `manage_resources.py` — Updated `create()` Method

```python
class ResourceManager:
    def __init__(self, params):
        # ... existing init ...

        # Active Ansible tags for per-step filtering
        self.active_tags = params.get('active_tags', [])

    def create(self):
        pipeline = self.pipelines.get(self.fabric_type)
        if pipeline is None:
            return {'failed': True, 'msg': f"No create pipeline for '{self.fabric_type}'", 'results': []}

        # Filter pipeline steps by active tags
        pipeline = RegistryLoader.filter_pipeline_by_tags(pipeline, self.active_tags)

        display.v(
            f"{self.class_name}: Pipeline has {len(pipeline)} steps "
            f"after tag filtering (active_tags={self.active_tags})"
        )

        step_results = []
        for step in pipeline:
            # ... existing step execution logic (unchanged) ...
```

#### ActionModule `run()` — Pass Tags Through

```python
class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        # ... existing validation ...

        params = {
            # ... existing params ...
            'active_tags': task_vars.get('ansible_run_tags', []),  # NEW
        }

        manager = ResourceManager(params)
        create_result = manager.create()
        # ...
```

The same pattern applies to `ResourceRemover` and `remove_resources.py`.

### 5.4 Role YAML — No Changes Needed

The `main_v2.yml` files already apply the correct aggregate tag lists:

```yaml
# Already correct — triggers on ANY matching tag, plugin handles selectivity
- name: Create Resources in Nexus Dashboard
  cisco.nac_dc_vxlan.dtc.manage_resources:
    ...
  tags: "{{ nac_tags.create }}"    # [cr_manage_fabric, ..., cr_manage_policy]
```

The YAML task ensures Ansible's native tag evaluation triggers the plugin. The plugin then performs the fine-grained filtering internally.

### 5.5 Tag Validation — No Changes Needed

The existing `verify_tags` plugin and `nac_tags.all` list remain unchanged. They validate user-supplied tags before any role executes.

### 5.6 `common_global/vars/main.yml` — No Changes Needed

The `nac_tags` dict remains the single source of truth for:
- Ansible-level task tag application (via `tags: "{{ nac_tags.create }}"`)
- Tag validation (via `verify_tags` plugin)

The pipeline YAML files reference the **atomic tag values** (`cr_manage_fabric`, `rr_manage_interfaces`) — the same values defined inside `nac_tags`. No duplication of logic; the YAML pipeline just declares which atomic tag controls each step.

---

## 6. Updated File Inventory

### Files Modified

| File | Change | Scope |
|------|--------|-------|
| `objects/create_pipelines.yml` | Add `tag:` field to each step | All 6 fabric types |
| `objects/remove_pipelines.yml` | Add `tag:` field to each step | All 6 fabric types |
| `plugins/plugin_utils/registry_loader.py` | Add `filter_pipeline_by_tags()` static method | ~15 lines |
| `plugins/action/dtc/manage_resources.py` | Pass `active_tags`, call filter before loop | ~5 lines changed |
| `plugins/action/dtc/remove_resources.py` | Pass `active_tags`, call filter before loop | ~5 lines changed |

### Files NOT Modified

| File | Reason |
|------|--------|
| `roles/common_global/vars/main.yml` | `nac_tags` dict is already correct |
| `roles/common_global/tasks/main.yml` | `verify_tags` call is already correct |
| `plugins/action/dtc/verify_tags.py` | Validation logic is unchanged |
| `roles/dtc/create/tasks/main_v2.yml` | Already uses `tags: "{{ nac_tags.create }}"` |
| `roles/dtc/remove/tasks/main_v2.yml` | Already uses `tags: "{{ nac_tags.remove }}"` |
| `roles/dtc/common/tasks/main_v2.yml` | Common role tags (`common_role`) don't need step-level granularity |
| `objects/resource_types.yml` | Build step tags not needed — common role always builds everything |

---

## 7. Migration Considerations

### Why `build_resource_data` (Common Role) Does NOT Need Tags

The common role's `build_resource_data` plugin always runs the full build pipeline. This is by design:
- Building resource data is cheap (template rendering + file I/O)
- Change detection flags are computed during the build
- Create and remove roles depend on the complete `resource_data` and `change_flags` output
- Selectively building only some resources would leave incomplete change flags, causing downstream roles to malfunction

The common role task carries `tags: "{{ nac_tags.common_role }}"` which includes all `cr_manage_*` and `rr_manage_*` tags. This ensures the build always runs when any create or remove tag is active.

### Interaction Between Tags and Change Flags

Tags and change flags are **independent filter layers** applied in sequence:

```
Pipeline Step → Tag Filter → Change Flag Guard → Data Availability → Execute
                   │                  │                  │
                 "Should I           "Did this          "Is there
                  run this?"         resource           any data?"
                                     change?"
```

- **Tags:** Operator-controlled ("I only want to manage fabric and switches")
- **Change flags:** Data-controlled ("Only run if the data model changed for this resource")
- **Data availability:** Safety check ("Skip if there's nothing to send")

A step only executes if ALL three filters pass.

### Behavior Matrix

| `--tags` | Pipeline Tag | Change Flag | Data | Result |
|----------|-------------|-------------|------|--------|
| `all` (or none) | any | `true` | present | **Execute** |
| `cr_manage_fabric` | `cr_manage_fabric` | `true` | present | **Execute** |
| `cr_manage_fabric` | `cr_manage_switches` | `true` | present | **Skip (tag filtered)** |
| `cr_manage_switches` | `cr_manage_switches` | `false` | present | **Skip (change flag)** |
| `cr_manage_switches` | `cr_manage_switches` | `true` | empty | **Skip (no data)** |

### Backward Compatibility

The hybrid approach is **fully backward-compatible**:

- Operators who never use `--tags` see no behavior change (everything runs)
- Operators who use `--tags cr_manage_fabric` get the **same selective behavior** as the original YAML-based tasks
- The `verify_tags` validation pipeline is unchanged
- The `nac_tags` variable structure is unchanged

### `--list-tags` Limitation

Ansible's `--list-tags` command performs **static analysis** of YAML files. It will show the tags applied to the `manage_resources` and `remove_resources` tasks (`nac_tags.create` / `nac_tags.remove`), but it cannot introspect into the Python plugin to show per-step tags.

This is an inherent limitation of the Pythonic consolidation pattern. The workaround is documentation — the pipeline YAML files serve as the human-readable tag reference, and the `nac_tags` dict in `common_global/vars/main.yml` continues to provide the complete tag inventory.

### Tag Coupling: Steps That Share a Tag

Some pipeline steps are semantically coupled and share a tag:

| Tag | Steps | Reason |
|-----|-------|--------|
| `cr_manage_vpc_peers` | `vpc_peering`, `config_save` | Config-save is required after vPC peering changes |
| `cr_manage_vrfs_networks` | `vrfs_networks` (VRFs + Networks) | VRFs must be created before Networks |

This coupling is preserved in the YAML pipeline — both steps carry the same `tag` value. When the operator runs `--tags cr_manage_vpc_peers`, both the vPC peering creation AND the config-save execute together.

---

## Summary

| Aspect | Decision |
|--------|----------|
| **Where tags are defined** | `roles/common_global/vars/main.yml` — unchanged |
| **Where tags are mapped to steps** | `objects/create_pipelines.yml` and `objects/remove_pipelines.yml` — `tag:` field per step |
| **Where tag filtering happens** | Python plugins — `RegistryLoader.filter_pipeline_by_tags()` |
| **How active tags reach the plugin** | `task_vars['ansible_run_tags']` passed through `ActionModule.run()` |
| **Common role behavior** | No per-step tags — always builds everything |
| **OCP compliance** | Adding a new tagged step = YAML-only change |
| **Backward compatibility** | Full — same `--tags` CLI, same `verify_tags` validation |

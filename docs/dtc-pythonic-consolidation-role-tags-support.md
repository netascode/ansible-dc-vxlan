# DTC Pythonic Consolidation — Role-Level Tags Support

> **Date:** March 6, 2026
> **Scope:** How to extend the hybrid tag filtering approach to support the role-level tags (`role_create`, `role_remove`, `role_deploy`) in addition to the per-resource atomic tags (`cr_manage_*`, `rr_manage_*`).

---

## Table of Contents

1. [The Two-Level Tag Hierarchy](#1-the-two-level-tag-hierarchy)
2. [How Role-Level Tags Work Today](#2-how-role-level-tags-work-today)
3. [The Gap in the Current Hybrid Design](#3-the-gap-in-the-current-hybrid-design)
4. [Recommended Implementation](#4-recommended-implementation)
5. [Updated Filter Logic](#5-updated-filter-logic)
6. [Impact on Existing Files](#6-impact-on-existing-files)

---

## 1. The Two-Level Tag Hierarchy

The `nac_dc_vxlan` collection uses a two-level tag hierarchy:

| Level | Tags | Applied By | Purpose |
|-------|------|-----------|---------|
| **Playbook-level** | `role_create`, `role_deploy`, `role_remove` | `roles:` keyword in playbook YAML | Gate entire role execution via `--tags` |
| **Task-level** | `cr_manage_fabric`, `cr_manage_switches`, `rr_manage_interfaces`, etc. | `tags:` on `import_tasks` within role | Granular per-resource filtering within a role |

The playbook applies role-level tags to every task within a role:

```yaml
# vxlan.yaml
roles:
  - role: cisco.nac_dc_vxlan.dtc.create
    tags: 'role_create'

  - role: cisco.nac_dc_vxlan.dtc.deploy
    tags: 'role_deploy'

  - role: cisco.nac_dc_vxlan.dtc.remove
    tags: 'role_remove'
```

This means Ansible applies the `role_create` tag to **every task** inside the create role, the `role_deploy` tag to every task in deploy, and `role_remove` to every task in remove.

---

## 2. How Role-Level Tags Work Today

### Operator Usage

```bash
# Run only the create role (skip deploy and remove)
ansible-playbook vxlan.yaml --tags role_create

# Run create and deploy (skip remove)
ansible-playbook vxlan.yaml --tags role_create,role_deploy

# Run only the remove role
ansible-playbook vxlan.yaml --tags role_remove

# Run a specific resource within create
ansible-playbook vxlan.yaml --tags cr_manage_fabric
```

### Why `role_create` Also Runs Common/Validate Tasks

The `nac_tags.common_role` and `nac_tags.validate_role` tag lists **include** `role_create`, `role_deploy`, and `role_remove`:

```yaml
nac_tags:
  common_role:
    - role_create       # ← ensures common role runs when --tags role_create
    - role_deploy
    - role_remove
    - cr_manage_fabric
    - cr_manage_switches
    # ... all cr_manage_* and rr_manage_*

  validate_role:
    - role_validate
    - role_create       # ← ensures validate role runs when --tags role_create
    - role_deploy
    - role_remove
    # ... all cr_manage_* and rr_manage_*
```

So when a user runs `--tags role_create`:
1. The **create role** runs (playbook-level `tags: 'role_create'` matches)
2. The **common role** runs (its tasks tagged with `nac_tags.common_role` include `role_create`)
3. The **validate role** runs (its tasks tagged with `nac_tags.validate_role` include `role_create`)
4. The **deploy role** does NOT run (playbook-level `tags: 'role_deploy'` does not match `role_create`)
5. The **remove role** does NOT run (playbook-level `tags: 'role_remove'` does not match `role_create`)

### Inside the Create Role

Today's `sub_main_vxlan.yml` applies per-resource tags to each `import_tasks`:

```yaml
- name: Create Fabric
  import_tasks: common/fabric.yml
  tags: "{{ nac_tags.create_fabric }}"      # → [cr_manage_fabric]

- name: Manage Switches
  import_tasks: common/devices.yml
  tags: "{{ nac_tags.create_switches }}"    # → [cr_manage_switches]
```

When the user runs `--tags role_create`, **all** tasks within the create role execute (because `role_create` is applied at the playbook level to the entire role). Per-resource tags like `cr_manage_fabric` only filter when the user explicitly passes them.

---

## 3. The Gap in the Current Hybrid Design

The hybrid tag analysis (in `dtc-pythonic-consolidation-tags-analysis.md`) proposed adding a `tag:` field to each pipeline step and filtering based on `ansible_run_tags`. However, the `filter_pipeline_by_tags()` logic only handles atomic per-resource tags:

```python
# Current proposed filter (incomplete)
@staticmethod
def filter_pipeline_by_tags(pipeline, active_tags):
    if not active_tags or 'all' in active_tags:
        return pipeline
    return [
        step for step in pipeline
        if step.get('tag') is None or step.get('tag') in active_tags
    ]
```

**The problem:** When a user runs `--tags role_create`:
- `ansible_run_tags = ['role_create']`
- The `manage_resources` task in `main_v2.yml` has `tags: "{{ nac_tags.create }}"` which resolves to `[cr_manage_fabric, cr_manage_switches, ...]`
- Ansible matches because `role_create` is applied at the playbook level to the entire role — so the task runs
- But inside the plugin, `active_tags = ['role_create']`
- No pipeline step has `tag: role_create` — they have `tag: cr_manage_fabric`, `tag: cr_manage_switches`, etc.
- The filter would **skip every step** because `'cr_manage_fabric' not in ['role_create']`

The same problem applies to `role_remove` and `role_deploy`.

---

## 4. Recommended Implementation

### Approach: Role-Level Tags as "Run All" Signals

Role-level tags (`role_create`, `role_remove`, `role_deploy`) are semantically equivalent to "run the entire role." They should be treated the same as `all` — they bypass per-step filtering.

The filter logic needs a concept of **role-level bypass tags** — tags that mean "run the full pipeline for this role, don't filter by step."

### Where to Define Bypass Tags

**Option A: Hardcode in the filter (simplest)**

The three role-level tags are stable and structural — they map 1:1 to the three roles. Adding them to the filter's bypass list is low-maintenance:

```python
ROLE_BYPASS_TAGS = {'role_create', 'role_remove', 'role_deploy', 'all'}
```

**Option B: Define in pipeline YAML (data-driven, recommended)**

Add a `role_tag` key at the pipeline root level, alongside the fabric-type pipelines:

```yaml
# objects/create_pipelines.yml
create_pipelines:
  role_tag: role_create          # NEW — role-level tag that bypasses per-step filtering

  VXLAN_EVPN:
    - resource_name: fabric
      module: dcnm_fabric
      state: merged
      change_flag_guard: changes_detected_fabric
      tag: cr_manage_fabric
    # ...
```

```yaml
# objects/remove_pipelines.yml
remove_pipelines:
  role_tag: role_remove          # NEW

  VXLAN_EVPN:
    - resource_name: edge_connections
      # ...
```

This keeps the role-tag mapping in YAML alongside the pipeline data, maintaining OCP principles.

**Option C: Define in a new `nac_tags.yml` registry (most data-driven)**

Create a new YAML registry that externalizes the full tag hierarchy, including which tags are role-level bypass tags:

```yaml
# objects/nac_tags.yml
tag_config:
  role_bypass_tags:
    - role_create
    - role_remove
    - role_deploy
    - all
```

This is the most extensible approach but may be over-engineering for a stable, small list.

### Recommended: Option B (Pipeline-Level `role_tag`)

Option B strikes the right balance — the bypass tag is declared alongside the pipeline it controls, and it's data-driven. If the role-level tag names ever change, it's a YAML edit.

---

## 5. Updated Filter Logic

### Updated `filter_pipeline_by_tags()`

```python
@staticmethod
def filter_pipeline_by_tags(pipeline, active_tags, role_tag=None):
    """
    Filter pipeline steps based on active Ansible run tags.

    Filtering rules (applied in order):
    1. No active tags → run all steps (no --tags specified)
    2. 'all' in active tags → run all steps (Ansible convention)
    3. role_tag in active tags → run all steps (role-level tag = entire role)
    4. Otherwise → include only steps whose tag matches an active tag
    5. Steps with no tag field (tag is None) → always included

    Args:
        pipeline:    List of pipeline step dicts from YAML registry
        active_tags: List of active Ansible tags (from ansible_run_tags)
        role_tag:    The role-level bypass tag (e.g., 'role_create')
                     from the pipeline registry's role_tag field

    Returns:
        Filtered list of pipeline steps
    """
    # Rules 1-3: No filtering conditions
    if not active_tags or 'all' in active_tags:
        return pipeline

    if role_tag and role_tag in active_tags:
        return pipeline

    # Rule 4-5: Per-step tag filtering
    return [
        step for step in pipeline
        if step.get('tag') is None or step.get('tag') in active_tags
    ]
```

### How It's Called from ResourceManager / ResourceRemover

```python
class ResourceManager:
    def __init__(self, params):
        # ... existing init ...
        self.active_tags = params.get('active_tags', [])

        # Load pipeline registry
        self.collection_path = RegistryLoader.get_collection_path()
        registry = RegistryLoader.load(self.collection_path, 'create_pipelines')
        self.pipelines = registry.get('create_pipelines', {})

        # Extract the role-level bypass tag from registry
        self.role_tag = self.pipelines.pop('role_tag', None)  # 'role_create'

    def create(self):
        pipeline = self.pipelines.get(self.fabric_type)
        # ...

        # Filter by tags — role_tag causes full pipeline execution
        pipeline = RegistryLoader.filter_pipeline_by_tags(
            pipeline, self.active_tags, self.role_tag
        )
        # ... execute filtered pipeline
```

### Behavior Matrix

| `--tags` Value | `active_tags` | `role_tag` | Filter Result |
|---------------|---------------|------------|---------------|
| *(none)* | `['all']` | `role_create` | **Run all** (rule 1: `all` in tags) |
| `role_create` | `['role_create']` | `role_create` | **Run all** (rule 3: role_tag matches) |
| `role_create,role_deploy` | `['role_create', 'role_deploy']` | `role_create` | **Run all** (rule 3: role_tag matches) |
| `cr_manage_fabric` | `['cr_manage_fabric']` | `role_create` | **Run fabric only** (rule 4: step tag matches) |
| `cr_manage_fabric,cr_manage_switches` | `['cr_manage_fabric', 'cr_manage_switches']` | `role_create` | **Run fabric + switches** (rule 4) |
| `role_remove` | `['role_remove']` | `role_create` | **Run none** ⚠️ (see note below) |

**Note on the last row:** If `--tags role_remove` is passed, the create role's `manage_resources` task would not even execute because Ansible's native tag evaluation at the playbook level gates it. The playbook applies `tags: 'role_create'` to the create role, which doesn't match `role_remove`. The task never reaches the plugin. This is handled at the Ansible level, not the Python level.

### Deploy Role Consideration

The deploy role (`role_deploy`) operates differently — it uses `fabric_deploy_manager` which is already a self-contained action plugin. The role-level tag `role_deploy` is handled entirely at the playbook level:

```yaml
# Playbook level
- role: cisco.nac_dc_vxlan.dtc.deploy
  tags: 'role_deploy'
```

The deploy role's internal tasks use `tags: "{{ nac_tags.deploy }}"` which resolves to `[role_deploy]`. Since deploy doesn't have per-resource granularity (it's a single operation), no per-step tag filtering is needed inside the deploy plugin. The `role_tag` pattern applies only to `manage_resources` (create) and `remove_resources` (remove).

---

## 6. Impact on Existing Files

### Files Modified

| File | Change |
|------|--------|
| `objects/create_pipelines.yml` | Add `role_tag: role_create` at pipeline root level; add `tag:` to each step |
| `objects/remove_pipelines.yml` | Add `role_tag: role_remove` at pipeline root level; add `tag:` to each step |
| `plugins/plugin_utils/registry_loader.py` | Update `filter_pipeline_by_tags()` to accept and check `role_tag` parameter |
| `plugins/action/dtc/manage_resources.py` | Extract `role_tag` from registry; pass to filter; pass `active_tags` from `task_vars` |
| `plugins/action/dtc/remove_resources.py` | Extract `role_tag` from registry; pass to filter; pass `active_tags` from `task_vars` |

### Files NOT Modified

| File | Reason |
|------|--------|
| `roles/common_global/vars/main.yml` | `nac_tags` dict already includes `role_create`, `role_deploy`, `role_remove` in all relevant lists |
| `roles/dtc/create/tasks/main_v2.yml` | Already uses `tags: "{{ nac_tags.create }}"` — Ansible handles playbook-level `role_create` tag inheritance |
| `roles/dtc/remove/tasks/main_v2.yml` | Already uses `tags: "{{ nac_tags.remove }}"` — same as above |
| `roles/dtc/deploy/tasks/main.yml` | No per-step filtering needed — deploy is a single operation |
| `plugins/action/dtc/verify_tags.py` | Validation unchanged — `role_create`, `role_remove`, `role_deploy` already in `nac_tags.all` |
| `plugins/action/dtc/build_resource_data.py` | Common role always builds everything — no tag filtering |
| `objects/resource_types.yml` | Build-phase tags not needed |
| `objects/fabric_types.yml` | No tag concept needed |

### Updated Pipeline YAML Example

```yaml
# objects/create_pipelines.yml
create_pipelines:
  role_tag: role_create                              # NEW — bypass tag for full-role execution

  VXLAN_EVPN:
    - resource_name: fabric
      module: dcnm_fabric
      state: merged
      change_flag_guard: changes_detected_fabric
      tag: cr_manage_fabric

    - resource_name: devices
      module: dcnm_inventory
      state: merged
      change_flag_guard: changes_detected_inventory
      tag: cr_manage_switches

    - resource_name: vpc_peering
      module: dcnm_links
      state: merged
      change_flag_guard: changes_detected_vpc_peering
      tag: cr_manage_vpc_peers

    - resource_name: config_save
      module: _config_save
      state: null
      change_flag_guard: changes_detected_vpc_peering
      tag: cr_manage_vpc_peers

    - resource_name: interfaces
      module: dcnm_interface
      state: replaced
      change_flag_guard: changes_detected_interfaces
      tag: cr_manage_interfaces

    - resource_name: edge_connections
      module: dcnm_links
      state: merged
      change_flag_guard: changes_detected_edge_connections
      tag: cr_manage_edge_connections

    - resource_name: vrfs_networks
      module: _vrfs_networks_pipeline
      state: null
      change_flag_guard: changes_detected_vrfs
      tag: cr_manage_vrfs_networks

    - resource_name: links
      module: dcnm_links
      state: merged
      change_flag_guard: changes_detected_fabric_links
      tag: cr_manage_links

    - resource_name: policies
      module: dcnm_policy
      state: merged
      change_flag_guard: changes_detected_policy
      tag: cr_manage_policy
  # ... (same pattern for eBGP_VXLAN, ISN, External, MSD, MCFG)
```

```yaml
# objects/remove_pipelines.yml
remove_pipelines:
  role_tag: role_remove                              # NEW — bypass tag for full-role execution

  VXLAN_EVPN:
    - resource_name: edge_connections
      module: dcnm_links
      state: deleted
      change_flag_guard: changes_detected_edge_connections
      tag: rr_manage_edge_connections

    - resource_name: policies
      module: dcnm_policy
      state: deleted
      change_flag_guard: changes_detected_policy
      tag: rr_manage_policy

    # ... (same pattern for remaining steps and fabric types)
```

---

## Summary

| Tag Type | Where Defined | Where Evaluated | Behavior |
|----------|--------------|-----------------|----------|
| `all` | Ansible built-in | `filter_pipeline_by_tags` | Bypass all filtering — run full pipeline |
| `role_create` | Playbook YAML + `create_pipelines.yml` `role_tag` | Ansible (playbook) + `filter_pipeline_by_tags` | Ansible gates which role runs; plugin runs full pipeline |
| `role_remove` | Playbook YAML + `remove_pipelines.yml` `role_tag` | Ansible (playbook) + `filter_pipeline_by_tags` | Ansible gates which role runs; plugin runs full pipeline |
| `role_deploy` | Playbook YAML | Ansible (playbook level only) | Ansible gates role execution; no per-step filtering needed |
| `cr_manage_*` | `common_global/vars/main.yml` + `create_pipelines.yml` step `tag` | Ansible (task tag) + `filter_pipeline_by_tags` | Ansible activates the task; plugin filters to matching steps only |
| `rr_manage_*` | `common_global/vars/main.yml` + `remove_pipelines.yml` step `tag` | Ansible (task tag) + `filter_pipeline_by_tags` | Ansible activates the task; plugin filters to matching steps only |

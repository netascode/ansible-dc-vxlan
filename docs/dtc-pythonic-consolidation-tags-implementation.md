# DTC Pythonic Consolidation — Tags Implementation

> **Date:** March 6, 2026
> **Scope:** Implementation of per-resource tag filtering within the consolidated action plugins, preserving the tag-based selective execution from the original per-task YAML approach.

---

## Problem

The Pythonic consolidation replaced ~50 YAML task files (each with their own Ansible `tags:`) with single action plugin calls (`manage_resources`, `remove_resources`). This collapsed all per-resource tags onto one task, meaning any matching tag triggered the **entire** pipeline — losing the granular selectivity operators relied on:

```bash
# INTENDED: Only create fabric
ansible-playbook vxlan.yaml --tags cr_manage_fabric

# ACTUAL (before this change): manage_resources runs the FULL create pipeline
# because the task carries ALL create tags and the plugin had no tag awareness
```

---

## Solution: Hybrid YAML Registry + Python Tag Filtering

### Design Principles

1. Pipeline YAML files declare which Ansible tag controls each step (`tag:` field)
2. Pipeline YAML files declare a role-level bypass tag (`role_tag:` field)
3. Python plugins read `ansible_run_tags` from `task_vars` and filter steps before execution
4. `common_global/vars/main.yml` remains the validation source — no changes needed
5. Infrastructure steps (no `tag:` field) always execute regardless of `--tags`

---

## Files Modified

### 1. `objects/create_pipelines.yml`

Added `role_tag: role_create` at the pipeline root level and a `tag:` field to each pipeline step across all 6 fabric types.

```yaml
create_pipelines:
  role_tag: role_create                    # NEW — bypass tag for full-role execution

  VXLAN_EVPN:
    - resource_name: fabric
      module: dcnm_fabric
      state: merged
      change_flag_guard: changes_detected_fabric
      tag: cr_manage_fabric                # NEW — per-step tag

    - resource_name: devices
      module: dcnm_inventory
      state: merged
      change_flag_guard: changes_detected_inventory
      tag: cr_manage_switches              # NEW
    # ... (same pattern for all steps and fabric types)
```

Steps without a `tag:` field (e.g., `_manage_child_fabrics`, `_prepare_msite_data`) are infrastructure steps that always execute — they are never filtered out.

### 2. `objects/remove_pipelines.yml`

Added `role_tag: role_remove` at the pipeline root level and a `tag:` field to each pipeline step across all 6 fabric types.

```yaml
remove_pipelines:
  role_tag: role_remove                    # NEW — bypass tag for full-role execution

  VXLAN_EVPN:
    - resource_name: edge_connections
      module: dcnm_links
      state: deleted
      change_flag_guard: changes_detected_edge_connections
      tag: rr_manage_edge_connections      # NEW

    - resource_name: policies
      module: dcnm_policy
      state: deleted
      change_flag_guard: changes_detected_policy
      tag: rr_manage_policy                # NEW
    # ... (same pattern for all steps and fabric types)
```

### 3. `plugins/plugin_utils/registry_loader.py`

Added the `filter_pipeline_by_tags()` static method to `RegistryLoader`:

```python
@staticmethod
def filter_pipeline_by_tags(pipeline, active_tags, role_tag=None):
    """
    Filter pipeline steps based on active Ansible run tags.

    Filtering rules (applied in order):
    1. No active tags or empty → run all steps (no --tags specified)
    2. 'all' in active tags → run all steps (Ansible convention)
    3. role_tag in active tags → run all steps (role-level tag = entire role)
    4. Otherwise → include only steps whose tag matches an active tag
    5. Steps with no tag field (tag is None) → always included
    """
    if not active_tags or 'all' in active_tags:
        return pipeline

    if role_tag and role_tag in active_tags:
        return pipeline

    return [
        step for step in pipeline
        if step.get('tag') is None or step.get('tag') in active_tags
    ]
```

### 4. `plugins/action/dtc/manage_resources.py`

Three changes in `ResourceManager.__init__()` and `ResourceManager.create()`:

**`__init__`** — Accept `active_tags` and extract `role_tag` from registry:
```python
# Active Ansible tags for per-step filtering
self.active_tags = params.get('active_tags', [])

# Extract the role-level bypass tag from registry
self.role_tag = self.pipelines.pop('role_tag', None)
```

**`create()`** — Filter pipeline before the execution loop:
```python
pipeline = RegistryLoader.filter_pipeline_by_tags(
    pipeline, self.active_tags, self.role_tag
)
```

**`ActionModule.run()`** — Pass `ansible_run_tags` from `task_vars`:
```python
params = {
    # ... existing params ...
    'active_tags': task_vars.get('ansible_run_tags', []),
}
```

### 5. `plugins/action/dtc/remove_resources.py`

Same three changes as `manage_resources.py`, applied to `ResourceRemover`:

**`__init__`** — Accept `active_tags` and extract `role_tag`:
```python
self.active_tags = params.get('active_tags', [])
self.role_tag = self.pipelines.pop('role_tag', None)
```

**`remove()`** — Filter pipeline before the execution loop:
```python
pipeline = RegistryLoader.filter_pipeline_by_tags(
    pipeline, self.active_tags, self.role_tag
)
```

**`ActionModule.run()`** — Pass `ansible_run_tags`:
```python
params = {
    # ... existing params ...
    'active_tags': task_vars.get('ansible_run_tags', []),
}
```

---

## Files NOT Modified

| File | Reason |
|------|--------|
| `roles/common_global/vars/main.yml` | `nac_tags` dict already correct — no changes needed |
| `roles/dtc/create/tasks/main.yml` | Already uses `tags: "{{ nac_tags.create }}"` |
| `roles/dtc/remove/tasks/main.yml` | Already uses `tags: "{{ nac_tags.remove }}"` |
| `roles/dtc/common/tasks/main.yml` | Common role always builds everything — no per-step filtering needed |
| `plugins/action/dtc/verify_tags.py` | Tag validation unchanged |
| `plugins/action/dtc/build_resource_data.py` | Common role has no per-step tag granularity |
| `objects/resource_types.yml` | Build-phase tags not needed |
| `objects/fabric_types.yml` | No tag concept needed |

---

## Tag Scenarios Supported

| Scenario | `--tags` Value | Create Pipeline | Remove Pipeline |
|----------|---------------|-----------------|-----------------|
| No tags specified | *(none)* | **Run all** | **Run all** |
| Ansible `all` | `all` | **Run all** | **Run all** |
| Role-level create | `role_create` | **Run all** | *(not triggered — Ansible playbook-level gating)* |
| Role-level remove | `role_remove` | *(not triggered)* | **Run all** |
| Role-level deploy | `role_deploy` | *(not triggered)* | *(not triggered)* |
| Single resource | `cr_manage_fabric` | **Fabric only** + infrastructure steps | *(not triggered)* |
| Multiple resources | `cr_manage_fabric,cr_manage_switches` | **Fabric + switches** + infrastructure steps | *(not triggered)* |
| Role + resource | `role_create,cr_manage_fabric` | **Run all** (role_tag bypasses) | *(not triggered)* |
| Remove resource | `rr_manage_interfaces` | *(not triggered)* | **Interfaces only** + infrastructure steps |

---

## Tag-to-Step Mapping

### Create Pipeline Tags

| Tag | Pipeline Steps |
|-----|---------------|
| `cr_manage_fabric` | `fabric` |
| `cr_manage_switches` | `devices` |
| `cr_manage_vpc_peers` | `vpc_peering`, `config_save` (coupled — both share the same tag) |
| `cr_manage_interfaces` | `interfaces` |
| `cr_manage_edge_connections` | `edge_connections` |
| `cr_manage_vrfs_networks` | `vrfs_networks` |
| `cr_manage_links` | `links` |
| `cr_manage_policy` | `policies` |

### Remove Pipeline Tags

| Tag | Pipeline Steps |
|-----|---------------|
| `rr_manage_edge_connections` | `edge_connections` |
| `rr_manage_policy` | `policies` |
| `rr_manage_interfaces` | `interfaces` |
| `rr_manage_networks` | `networks` |
| `rr_manage_vrfs` | `vrfs` |
| `rr_manage_links` | `links` |
| `rr_manage_vpc_peers` | `vpc_peers` |
| `rr_manage_switches` | `switches` |

### Infrastructure Steps (No Tag — Always Execute)

| Fabric Type | Steps |
|-------------|-------|
| MSD | `child_fabrics`, `msite_data`, `bgw_anycast` |
| MCFG | `child_fabrics`, `msite_data` |

---

## Filter Execution Order

Tags and change flags are independent filter layers applied in sequence:

```
Pipeline Step → Tag Filter → Change Flag Guard → Data Availability → Execute
                   │                  │                  │
                 "Should I           "Did this          "Is there
                  run this?"         resource           any data?"
                                     change?"
```

A step only executes if **all three** filters pass.

---

## Backward Compatibility

- Operators who never use `--tags` see **no behavior change** (everything runs)
- Operators who use `--tags cr_manage_fabric` get the **same selective behavior** as the original YAML-based tasks
- The `verify_tags` validation pipeline is **unchanged**
- The `nac_tags` variable structure is **unchanged**

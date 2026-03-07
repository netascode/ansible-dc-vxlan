# DTC Pythonic Consolidation — SOLID Principles Analysis

> **Date:** March 6, 2026
> **Scope:** Architecture review of the v2 design (`dtc-pythonic-consolidation-design-v2.md`) and its implementation files against the five Python SOLID design principles.

---

## Architecture Under Review

The DTC Pythonic Consolidation replaces ~2500 lines of repetitive Ansible YAML task files with a data-driven Python action plugin architecture. The key components are:

| Component | Location | Purpose |
|-----------|----------|---------|
| `RegistryLoader` | `plugins/plugin_utils/registry_loader.py` | Load and cache YAML registry files |
| `ResourceBuilder` + `ActionModule` | `plugins/action/dtc/build_resource_data.py` | Template→Render→Diff→Flag pipeline |
| `ResourceManager` + `ActionModule` | `plugins/action/dtc/manage_resources.py` | Ordered NDFC resource creation |
| `ResourceRemover` + `ActionModule` | `plugins/action/dtc/remove_resources.py` | Ordered NDFC resource removal |
| `FabricTypeRegistry` | `plugins/plugin_utils/fabric_type_registry.py` | Fabric-type namespace/feature lookup |
| `resource_types.yml` | `objects/resource_types.yml` | 25 resource type definitions |
| `create_pipelines.yml` | `objects/create_pipelines.yml` | Ordered creation operations per fabric type |
| `remove_pipelines.yml` | `objects/remove_pipelines.yml` | Reverse-ordered removal operations per fabric type |
| `fabric_types.yml` | `objects/fabric_types.yml` | Fabric-type namespace and feature mappings |

All paths are relative to collection root:
`vxlan-as-code/collections/ansible_collections/cisco/nac_dc_vxlan/`

---

## S — Single Responsibility Principle

**Rating: ✅ Strong**

Each class has a clearly bounded responsibility:

| Class | Single Responsibility |
|-------|----------------------|
| `RegistryLoader` | Load and cache YAML registry files |
| `ResourceBuilder` | Template→Render→Diff→Flag pipeline |
| `ResourceManager` | Ordered NDFC resource creation |
| `ResourceRemover` | Ordered NDFC resource removal |
| `FabricTypeRegistry` | Fabric-type namespace/feature lookup |
| `ActionModule` (×3) | Ansible interface adapter (parameter validation, error handling) |

The Class + ActionModule split is textbook SRP — domain logic is separated from framework plumbing. Each domain class has exactly one reason to change: if its pipeline behavior changes. Each `ActionModule` only changes if the Ansible interface contract changes.

### Minor Tension

`ResourceBuilder` owns both template rendering *and* diff/change-detection. These are arguably two responsibilities. The design doc (Key Decision #4) justifies merging `diff_compare` and `diff_model_changes` into the builder because "they're just method calls within the pipeline." This is pragmatically sound — they are always called together in sequence and share no consumers outside the build pipeline — but if diff logic grows significantly, extracting a `ChangeDetector` helper would strengthen SRP further.

---

## O — Open/Closed Principle

**Rating: ✅ Excellent**

This is the architecture's strongest SOLID dimension. The YAML externalization is specifically designed for OCP:

| Extension Scenario | Change Required | Python Changes |
|--------------------|-----------------|----------------|
| Add a new resource type | Add 6-8 lines to `objects/resource_types.yml` | **None** |
| Add a new fabric type | Add entries to `fabric_types.yml`, `create_pipelines.yml`, `remove_pipelines.yml` | **None** |
| Reorder pipeline steps | Edit YAML pipeline file | **None** |
| Change a module state | Edit YAML pipeline file | **None** |
| Add a new creation step | Add entry to `create_pipelines.yml` | **None** |
| Add a new removal step | Add entry to `remove_pipelines.yml` | **None** |

The core Python plugins are **closed for modification** while the YAML registries are **open for extension**.

### One Area of Reduced OCP

The `getattr(self, module)` dispatch for internal methods (prefixed with `_`) is the one area where OCP is weaker — adding a new internal method (like `_vrfs_networks_pipeline`) requires modifying the Python class. However, this is an acceptable trade-off since internal methods encode business logic that cannot be expressed declaratively in YAML.

---

## L — Liskov Substitution Principle

**Rating: ✅ Adequate**

All three `ActionModule` classes extend `ActionBase` and follow the same contract:

```python
def run(self, tmp=None, task_vars=None) -> dict:
    results = super().run(tmp, task_vars)
    # ... validate, execute, return results dict
```

They can be substituted anywhere Ansible expects an action plugin. The return dict follows a consistent schema (`failed`, `msg`, plus plugin-specific keys like `results`, `resource_data`, `change_flags`).

### Observation

The domain classes (`ResourceBuilder`, `ResourceManager`, `ResourceRemover`) do not share an explicit base class or protocol. They follow a *de facto* convention (constructor takes `params` dict, entry method returns a result dict), but this is not enforced. LSP does not strictly require a shared base — these classes are never interchangeable — but defining a `Protocol` or abstract base would make the implicit contract explicit:

```python
class DtcPipeline(Protocol):
    def __init__(self, params: dict) -> None: ...
    # No shared entry method needed — each pipeline has its own verb
```

This is minor since the three classes are never substituted for one another. They serve distinct pipeline stages (build, create, remove) with different entry methods (`build_all()`, `create()`, `remove()`).

---

## I — Interface Segregation Principle

**Rating: ✅ Good**

The `ActionModule` interfaces are appropriately scoped — no caller is forced to supply parameters it does not use:

### `build_resource_data` Parameters
| Parameter | Required | Purpose |
|-----------|----------|---------|
| `fabric_type` | Yes | Fabric type selector |
| `fabric_name` | Yes | Fabric identifier |
| `data_model` | Yes | Extended data model |
| `role_path` | Yes | Path to the common role |
| `check_roles` | Yes | Check roles configuration |
| `force_run_all` | No (default: `false`) | Force full run |
| `run_map_diff_run` | No (default: `true`) | Diff-based run flag |

### `manage_resources` Parameters
| Parameter | Required | Purpose |
|-----------|----------|---------|
| `fabric_type` | Yes | Fabric type selector |
| `fabric_name` | Yes | Fabric identifier |
| `data_model` | Yes | Extended data model |
| `resource_data` | Yes | Output from build_resource_data |
| `change_flags` | Yes | Change detection flags |
| `nd_version` | No | Nexus Dashboard version |

### `remove_resources` Parameters
| Parameter | Required | Purpose |
|-----------|----------|---------|
| `fabric_type` | Yes | Fabric type selector |
| `fabric_name` | Yes | Fabric identifier |
| `data_model` | Yes | Extended data model |
| `resource_data` | Yes | Output from build_resource_data |
| `change_flags` | Yes | Change detection flags |
| `run_map_diff_run` | No (default: `true`) | Diff-based run flag |
| `force_run_all` | No (default: `false`) | Force full run |
| `interface_delete_mode` | No (default: `false`) | Enable interface deletion |
| `stage_remove` | No (default: `false`) | Stage changes without deploying |

### Area to Watch

`remove_resources` has the most parameters (9). If this grows further, consider grouping related parameters into a sub-dict:

```yaml
execution_mode:
  diff_run: true
  force_run_all: false
  interface_delete_mode: false
```

### RegistryLoader

`RegistryLoader` exposes only three methods — clean and minimal:

| Method | Purpose |
|--------|---------|
| `load(collection_path, registry_name)` | Load and cache a YAML registry |
| `get_collection_path()` | Derive collection root from file location |
| `clear_cache()` | Clear the LRU cache (testing support) |

---

## D — Dependency Inversion Principle

**Rating: ⚠️ Partial**

### What Works Well

1. **RegistryLoader as an abstraction over file I/O:** Domain classes depend on `RegistryLoader` rather than scattering raw `yaml.safe_load` calls throughout.

2. **YAML registries as configuration abstractions:** Plugins depend on the *schema* of the registry data, not on where or how it is stored.

3. **NDFC interaction via `_execute_module()`:** The plugins do not import or instantiate `cisco.dcnm` modules directly — they use Ansible's action plugin execution interface as an abstraction layer.

### Where It Falls Short

#### 1. Concrete Dependency on RegistryLoader

The domain classes import and call `RegistryLoader` directly rather than receiving registry data via injection:

```python
# Current (concrete dependency):
class ResourceBuilder:
    def __init__(self, params):
        registry = RegistryLoader.load(self.collection_path, 'resource_types')
        self.resource_types = registry.get('resource_types', {})

# Strict DIP (injected dependency):
class ResourceBuilder:
    def __init__(self, params, registry_data):
        self.resource_types = registry_data
```

Constructor injection would improve unit testability — mock registry data could be passed directly without patching `RegistryLoader`. However, Ansible action plugins conventionally construct their collaborators internally, and `RegistryLoader` with `lru_cache` is effectively a singleton. The pragmatic cost of the current approach is low.

#### 2. Module-Level Constants in Python

`FABRIC_SUBDIR_MAP` and `INTERFACE_TYPES` remain as module-level constants in `build_resource_data.py` (lines 39-56). These could be externalized:

- **`FABRIC_SUBDIR_MAP`** partially overlaps with `fabric_types.yml` which already has a `file_subdir` field for each fabric type. The design doc's `_fabric_subdir()` method notes: *"This could also come from `fabric_types.yml` via `FabricTypeRegistry`."*

- **`INTERFACE_TYPES`** could be derived from `resource_types.yml` by adding an `is_interface: true` flag to each interface resource type, then filtering dynamically.

#### 3. Implicit Method Contract via `getattr`

The `getattr(self, module)` dispatch creates an implicit dependency between YAML pipeline definitions and Python method names. There is no formal interface declaring which internal methods exist — the YAML must exactly match method names on the class. This is not a DIP violation per se, but it creates tight coupling between data and implementation.

---

## Summary Scorecard

| Principle | Rating | Notes |
|-----------|--------|-------|
| **S** — Single Responsibility | ✅ Strong | Clean Class + ActionModule separation. Minor note: ResourceBuilder owns rendering + diffing |
| **O** — Open/Closed | ✅ Excellent | YAML externalization is purpose-built for extension without modification |
| **L** — Liskov Substitution | ✅ Adequate | ActionModules are proper ActionBase subtypes. Domain classes have no shared base (not needed) |
| **I** — Interface Segregation | ✅ Good | Each plugin takes only what it needs. RegistryLoader is minimal |
| **D** — Dependency Inversion | ⚠️ Partial | RegistryLoader used directly rather than injected. Two constants remain in Python |

---

## Recommended Improvements

Ordered by priority and impact:

### 1. Move `FABRIC_SUBDIR_MAP` into `fabric_types.yml` (Low Effort, High Consistency)

The `fabric_types.yml` registry already has a `file_subdir` field for each fabric type. Remove the duplicate `FABRIC_SUBDIR_MAP` dict from `build_resource_data.py` and read it from the registry instead. This eliminates the last hardcoded dispatch map from Python.

### 2. Move `INTERFACE_TYPES` into `resource_types.yml` (Low Effort, High Consistency)

Add an `is_interface: true` flag to each interface resource type entry in the registry. Then derive the interface type list dynamically:

```python
interface_types = [
    name for name, cfg in self.resource_types.items()
    if cfg.get('is_interface', False)
]
```

This means adding a new interface type automatically includes it in `interface_all` — no Python change needed.

### 3. Inject Registry Data via Constructor (Medium Effort, High Testability)

Pass parsed registry dicts into domain classes from the ActionModule instead of having domain classes call `RegistryLoader.load()` directly:

```python
# In ActionModule.run():
collection_path = RegistryLoader.get_collection_path()
registry_data = RegistryLoader.load(collection_path, 'resource_types')

params['resource_types'] = registry_data.get('resource_types', {})
builder = ResourceBuilder(params)
```

This improves DIP compliance and makes unit testing straightforward — pass mock data without patching.

### 4. Document Internal Method Contract (Low Effort, Clarity)

Add a docstring or validation to document the implicit contract that internal pipeline methods (prefixed with `_`) in YAML must match method names on the domain class:

```python
# In create()/remove() pipeline loop:
if module.startswith('_'):
    if not hasattr(self, module):
        raise ValueError(
            f"Pipeline references internal method '{module}' "
            f"but {self.class_name} has no such method"
        )
    result = getattr(self, module)(resource_name, data)
```

This converts a silent `AttributeError` into a descriptive error message.

---

## Conclusion

The architecture adheres well to SOLID principles, with particular strength in OCP (Open/Closed) through its YAML-driven registry design. The primary improvement area is DIP (Dependency Inversion), where constructor injection of registry data would improve both testability and principle compliance. The remaining recommendations are incremental refinements that would bring the architecture closer to full SOLID alignment without changing its fundamental structure.

The design is well-suited to the Ansible action plugin ecosystem, where framework conventions (ActionBase inheritance, `_execute_module` delegation) naturally constrain some architectural choices. The pragmatic trade-offs made are appropriate for the context.

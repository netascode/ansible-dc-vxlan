# DTC Pythonic Consolidation — Tags Integration SOLID Analysis

> **Date:** March 6, 2026
> **Scope:** SOLID principles assessment of the hybrid tag filtering approach proposed in `dtc-pythonic-consolidation-tags-analysis.md` and its impact on the existing v2 architecture.

---

## Context

The hybrid tag approach adds:

1. A `tag:` field to each pipeline step in `create_pipelines.yml` and `remove_pipelines.yml`
2. A `filter_pipeline_by_tags()` static method (on `RegistryLoader` or standalone `TagFilter`)
3. An `active_tags` parameter passed from `ActionModule.run()` into domain classes via `task_vars['ansible_run_tags']`

This restores per-resource tag selectivity that was lost when ~50 YAML task files were consolidated into single action plugin calls.

---

## S — Single Responsibility Principle

**Rating: ✅ No Degradation**

`filter_pipeline_by_tags()` is a single-purpose static method. Whether it lives on `RegistryLoader` (Option A) or in a standalone `TagFilter` class (Option B), the filtering concern is isolated. The domain classes (`ResourceManager`, `ResourceRemover`) call it once before their pipeline loop — they do not absorb tag-matching logic into their execution code.

### Design Choice: Where to Place the Filter

| Option | SRP Impact |
|--------|------------|
| **Option A:** `RegistryLoader.filter_pipeline_by_tags()` | Slightly blurs SRP — `RegistryLoader` becomes "load YAML + filter pipeline data" |
| **Option B:** Standalone `TagFilter` class in `tag_filter.py` | Clean SRP — `RegistryLoader` stays focused on I/O, `TagFilter` owns filtering |

Either way the impact is minimal since the filter is stateless and ~10 lines. Option B is the stricter choice.

---

## O — Open/Closed Principle

**Rating: ✅ Strengthened**

This is the key improvement. The hybrid approach elevates what was previously a gap (tags vanished when tasks were consolidated) back to full data-driven extensibility:

| Extension Scenario | Change Required | Python Changes |
|--------------------|-----------------|----------------|
| Add a new tagged pipeline step | Add entry with `tag:` field to pipeline YAML | **None** |
| Change which tag controls a step | Edit the `tag:` value in pipeline YAML | **None** |
| Share a tag across coupled steps | Set same `tag:` value on both steps | **None** |
| Add a step that always runs (no tag filtering) | Omit the `tag:` field (or set to `null`) | **None** |

The filter logic is generic — `step.get('tag') in active_tags` — with no resource-specific or tag-specific code. Adding a new tag or changing a tag mapping is a YAML-only change, consistent with the existing OCP design for pipeline steps, change flag guards, and resource types.

---

## L — Liskov Substitution Principle

**Rating: ✅ Unchanged**

The `ActionModule` classes still properly extend `ActionBase` with the same `run(self, tmp=None, task_vars=None) -> dict` contract. The new `active_tags` parameter flows through the same `params` dict pattern used for all other parameters — no contract change.

---

## I — Interface Segregation Principle

**Rating: ✅ Unchanged**

`active_tags` is an optional parameter that defaults to `[]` (no filtering — run everything). Callers that do not need tag filtering are unaffected:

| Plugin | Receives `active_tags`? | Reason |
|--------|------------------------|--------|
| `build_resource_data` | **No** | Common role always builds everything — per-step tags would break change detection |
| `manage_resources` | **Yes** | Create pipeline needs per-step selectivity |
| `remove_resources` | **Yes** | Remove pipeline needs per-step selectivity |

No caller is forced to supply a parameter it does not use. The filter method itself has a clean two-argument signature: `filter(pipeline, active_tags)`.

---

## D — Dependency Inversion Principle

**Rating: ⚠️ Same as Before**

The same partial DIP situation exists — `filter_pipeline_by_tags()` is called directly rather than injected. However:

- The filtering is a **pure function** (input list → filtered list, no side effects)
- It has no dependencies of its own (no file I/O, no state)
- The pragmatic cost of the direct call is low

If constructor injection is adopted for registry data (Recommendation #3 from the SOLID analysis), the filtered pipeline could be passed in as well:

```python
# In ActionModule.run():
pipeline = RegistryLoader.load(collection_path, 'create_pipelines')
filtered = TagFilter.filter(pipeline.get('create_pipelines', {})[fabric_type], active_tags)
params['pipeline'] = filtered
manager = ResourceManager(params)
```

This would bring the tag filtering into the same DIP-compliant injection pattern.

---

## Updated Scorecard

| Principle | Before Tags | After Tags | Change |
|-----------|-------------|------------|--------|
| **S** — Single Responsibility | ✅ Strong | ✅ Strong | No change (if TagFilter is standalone) |
| **O** — Open/Closed | ✅ Excellent | ✅ Excellent+ | **Improved** — tags extensible via YAML |
| **L** — Liskov Substitution | ✅ Adequate | ✅ Adequate | No change |
| **I** — Interface Segregation | ✅ Good | ✅ Good | No change — `active_tags` is optional |
| **D** — Dependency Inversion | ⚠️ Partial | ⚠️ Partial | No change |

---

## Conclusion

The hybrid tag filtering approach maintains full SOLID compliance and strengthens OCP. The architecture follows the same established pattern — declarative data in YAML, generic processing in Python. Tag-to-step mappings are data-driven and extensible without code changes, consistent with how resource types, pipeline steps, and change flag guards already work.

The only design choice with SRP implications is where to place `filter_pipeline_by_tags()`. A standalone `TagFilter` utility (Option B) is the stricter choice; placing it on `RegistryLoader` (Option A) is pragmatically acceptable given the method's simplicity.

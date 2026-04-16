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
Phase 2 remote diff filter for underlay IP manual allocations.

Underlay IP Manual Allocation Filter (Phase 2 - Controller Reconciliation).

Queries the NDFC controller to determine which desired IP pool allocations
already exist and match expected values. Filters out allocations that are
already correct, returning only those needing controller updates.

Part of a two-phase comparison:
  Phase 1 (local YAML diff via common/files): detects data model changes
  Phase 2 (this plugin): reconciles desired state against controller state

The desired_config contains four allocation types:

  1. Routing Loopback IPs (device_interface scope, per-switch):
     entity_name: "<serial>~loopback0"       pool: LOOPBACK0_IP_POOL
     entity_name: "<serial>~loopback1"       pool: LOOPBACK1_IP_POOL

  2. VTEP Secondary IPs (device_interface scope, vPC pair):
     entity_name: "<serial1>~<serial2>~loopback1"  pool: LOOPBACK1_IP_POOL

  3. P2P / Backup Link Subnets (link scope, bidirectional):
     entity_name: "<serial1>~Vlan3600~<serial2>~Vlan3600"  pool: SUBNET
     Note: endpoint order may vary; _canonicalize_link_entity handles this.

  4. Per-endpoint IPs within a link subnet (device_interface scope):
     entity_name: "<serial>~Vlan3600"    pool: "10.4.1.0/31"
     The pool_name IS the allocated subnet from type 3 above.

Pools are auto-detected from desired_config pool_name values, or can be
explicitly overridden via the query_pools argument.

Returns:
  filtered_config: allocations needing controller updates (used by caller)
  missing_or_mismatch: observability log of what matched/mismatched
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.plugins.action import ActionBase


def _norm_text(value, lower=False):
    # Normalize text: strip whitespace, optionally lowercase. Handles None gracefully.
    if value is None:
        return ""
    text = str(value).strip()
    return text.lower() if lower else text


def _norm_entity(value):
    # Normalize entity names to lowercase for case-insensitive comparison.
    return _norm_text(value, lower=True)


def _norm_pool(value):
    # Normalize pool names to lowercase for case-insensitive comparison.
    return _norm_text(value, lower=True)


def _norm_scope(value):
    # NDFC uses varying scope type names (deviceinterface vs device_interface).
    # Canonicalize to match desired_config expectations.
    v = _norm_text(value, lower=True)
    if v in ["deviceinterface", "device_interface"]:
        return "deviceinterface"
    if v == "link":
        return "link"
    return v


def _parse_scope_filter(value):
    if value is None:
        return set()

    if isinstance(value, (list, tuple, set)):
        raw_values = list(value)
    else:
        text = _norm_text(value)
        if not text:
            return set()
        raw_values = [part.strip() for part in text.split(",") if part.strip()]

    scopes = set()
    for raw in raw_values:
        normalized = _norm_scope(raw)
        if normalized in ["", "all", "any", "*"]:
            return set()
        if normalized:
            scopes.add(normalized)

    return scopes


def _norm_resource(value):
    # Normalize resource values (IPs, names) to lowercase for comparison.
    text = _norm_text(value)
    if not text:
        return ""
    return text


def _canonicalize_link_entity(entity):
    """
    Canonicalize link entity format: tilde-separated endpoints (e.g., "device1~eth1~device2~eth2").
    Sort endpoints to handle bidirectional links consistently (link A-B == link B-A).
    """
    e = _norm_entity(entity)
    if not e:
        return ""

    parts = e.split("~")
    if len(parts) != 4:
        return e

    endpoint1 = parts[0] + "~" + parts[1]
    endpoint2 = parts[2] + "~" + parts[3]
    ordered = sorted([endpoint1, endpoint2])
    return ordered[0] + "~" + ordered[1]


def _extract_resource_items(data):
    """
    Recursively unwrap NDFC response envelopes to extract resource items.
    NDFC wraps resources in varying structures (DATA, data, resourceList, etc.);
    this function flattens them into a list of normalized items.
    """
    items = []

    if isinstance(data, list):
        for entry in data:
            items.extend(_extract_resource_items(entry))
        return items

    if not isinstance(data, dict):
        return items

    has_entity = any(k in data for k in ["entityName", "entity_name"])
    has_resource = any(
        k in data for k in ["resourceName", "resource", "value", "allocatedIp"]
    )
    if has_entity and has_resource:
        items.append(dict(data))

    for key in [
        "DATA",
        "data",
        "resourceList",
        "resources",
        "items",
        "allocations",
        "result",
    ]:
        nested = data.get(key)
        if nested is not None:
            items.extend(_extract_resource_items(nested))

    return items


class ActionModule(ActionBase):
    def _execute_ndfc_rest(self, method, path, task_vars, tmp):
        return self._execute_module(
            module_name="cisco.dcnm.dcnm_rest",
            module_args={
                "method": method,
                "path": path,
            },
            task_vars=task_vars,
            tmp=tmp,
        )

    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)

        # === INPUT PARSING AND VALIDATION ===
        desired_config = self._task.args.get("desired_config", []) or []
        fabric = self._task.args.get("fabric")
        query_pools = self._task.args.get("query_pools")
        scope_filter_arg = self._task.args.get("scope_filter", "all")
        allowed_scopes = _parse_scope_filter(scope_filter_arg)

        if not isinstance(desired_config, list):
            desired_config = []

        if not fabric:
            result.update({"failed": True, "msg": "fabric is required"})
            return result

        # === DETERMINE WHICH POOLS TO FILTER ===
        # If query_pools is explicitly provided, use it. Otherwise auto-detect
        # from desired_config pool_name values. No hardcoded defaults needed:
        # the data model already declares the exact pools it cares about.
        if query_pools:
            pools = {_norm_pool(pool) for pool in query_pools if _norm_text(pool)}
        else:
            pools = {
                _norm_pool(item.get("pool_name"))
                for item in desired_config
                if isinstance(item, dict) and item.get("pool_name") is not None
            }
            pools.discard("")

        # === BULK QUERY: SINGLE REST CALL FOR ALL FABRIC RESOURCES ===
        # Fetch all allocations in one call rather than per-pool queries to minimize
        # controller load and round-trip latency. Filtering happens client-side.
        path = "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/resource-manager/fabrics/{}".format(
            fabric
        )
        all_result = self._execute_ndfc_rest("GET", path, task_vars, tmp)

        query_errors = []
        all_existing_items = []
        if all_result.get("failed"):
            query_errors.append({"path": path, "msg": all_result.get("msg")})
        else:
            response = all_result.get("response", {})
            all_existing_items = _extract_resource_items(response)

        # === POOL AND SCOPE FILTERING OF BULK RESPONSE ===
        # Apply pool name, pool type, and scope filters to reduce the working set.
        filtered_existing_items = []
        for item in all_existing_items:
            pool_name = item.get("poolName")
            if pool_name is None:
                pool_name = item.get("pool_name")
            if pool_name is None:
                pool_name = item.get("pool")
            if pool_name is None and isinstance(item.get("resourcePool"), dict):
                pool_name = item.get("resourcePool", {}).get("poolName")

            normalized_pool = _norm_pool(pool_name)

            if pools and normalized_pool not in pools:
                continue

            scope_type = item.get("scopeType")
            if scope_type is None:
                scope_type = item.get("scope_type")
            if scope_type is None:
                scope_type = item.get("entityType")
            normalized_scope = _norm_scope(scope_type)
            if (
                allowed_scopes
                and normalized_scope
                and normalized_scope not in allowed_scopes
            ):
                continue

            filtered_existing_items.append(item)

        # === BUILD LOOKUP INDEXES ===
        # existing_map: (entity, pool) -> allocation details for exact entity+pool match.
        # existing_link_map: (canonical_link, pool) -> allocation for bidirectional link match.
        # existing_pool_resource_set: (pool, resource) -> fast check if resource is allocated.
        existing_map = {}
        existing_link_map = {}
        existing_pool_resource_set = set()

        for item in filtered_existing_items:
            entity_name = item.get("entityName")
            if entity_name is None:
                entity_name = item.get("entity_name")
            if entity_name is None:
                continue

            pool_name = item.get("poolName")
            if pool_name is None:
                pool_name = item.get("pool_name")
            if pool_name is None:
                pool_name = item.get("pool")
            if pool_name is None and isinstance(item.get("resourcePool"), dict):
                pool_name = item.get("resourcePool", {}).get("poolName")

            resource_value = item.get("resourceName")
            if resource_value is None:
                resource_value = item.get("resource")
            if resource_value is None:
                resource_value = item.get("value")
            if resource_value is None:
                resource_value = item.get("allocatedIp")

            scope_type = item.get("scopeType")
            if scope_type is None:
                scope_type = item.get("scope_type")
            if scope_type is None:
                scope_type = item.get("entityType")

            normalized_entity = _norm_entity(entity_name)
            normalized_pool = _norm_pool(pool_name)
            normalized_resource = _norm_resource(resource_value)
            normalized_scope = _norm_scope(scope_type)

            key = (normalized_entity, normalized_pool)

            existing_map[key] = {
                "entity": _norm_text(entity_name),
                "pool": _norm_text(pool_name),
                "resource": normalized_resource,
                "scope": normalized_scope,
                "raw_resource": _norm_text(resource_value),
            }

            if normalized_scope == "link":
                link_key = (_canonicalize_link_entity(entity_name), normalized_pool)
                existing_link_map[link_key] = existing_map[key]

            if normalized_pool and normalized_resource:
                existing_pool_resource_set.add((normalized_pool, normalized_resource))

        # === DESIRED VS EXISTING COMPARISON ===
        # Three-tier matching strategy: (1) exact entity+pool match, (2) canonical link match
        # for bidirectional links, (3) pool+resource fallback for unmatched allocations.
        # Only items missing or mismatched are added to filtered_config for update.
        filtered_config = []
        missing_or_mismatch = []
        matched_count = 0

        for item in desired_config:
            if not isinstance(item, dict):
                continue

            entity_name = item.get("entity_name")
            if entity_name is None:
                entity_name = item.get("entityName")
            pool_name = item.get("pool_name")
            scope_type = item.get("scope_type")

            expected_resource = _norm_resource(item.get("resource"))
            normalized_pool = _norm_pool(pool_name)
            normalized_entity = _norm_entity(entity_name)
            normalized_scope = _norm_scope(scope_type)

            # Skip items whose pool is not in the selected set
            if pools and normalized_pool not in pools:
                continue

            if (
                allowed_scopes
                and normalized_scope
                and normalized_scope not in allowed_scopes
            ):
                continue

            if not entity_name or not pool_name:
                filtered_config.append(item)
                missing_or_mismatch.append({
                    "reason": "missing_required_fields",
                    "entity": _norm_text(entity_name),
                    "pool": _norm_text(pool_name),
                    "scope": _norm_text(scope_type),
                    "expected": expected_resource,
                    "actual": "__unknown__",
                })
                continue

            # Tier 1: Exact entity+pool match
            existing = existing_map.get((normalized_entity, normalized_pool))
            matched_by = "exact"

            # Tier 2: Canonical link match for bidirectional links
            if existing is None and normalized_scope == "link":
                existing = existing_link_map.get(
                    (_canonicalize_link_entity(entity_name), normalized_pool)
                )
                if existing is not None:
                    matched_by = "canonical_link"

            # Tier 3: Pool+resource fallback (resource already allocated, entity may differ)
            if (
                existing is None
                and (normalized_pool, expected_resource) in existing_pool_resource_set
            ):
                matched_count += 1
                continue

            if existing is None:
                filtered_config.append(item)
                missing_or_mismatch.append({
                    "reason": "missing_in_nd",
                    "entity": _norm_text(entity_name),
                    "pool": _norm_text(pool_name),
                    "scope": _norm_text(scope_type),
                    "expected": expected_resource,
                    "actual": "__missing__",
                })
                continue

            actual_resource = existing.get("resource", "")
            if actual_resource != expected_resource:
                filtered_config.append(item)
                missing_or_mismatch.append({
                    "reason": "resource_mismatch",
                    "entity": _norm_text(entity_name),
                    "pool": _norm_text(pool_name),
                    "scope": _norm_text(scope_type),
                    "expected": expected_resource,
                    "actual": actual_resource,
                    "actual_raw": existing.get("raw_resource", ""),
                    "matched_by": matched_by,
                })
                continue

            matched_count += 1

        # === RESULT ASSEMBLY ===
        if query_errors:
            result.update({
                "failed": True,
                "msg": "Underlay all-resource query failed. Check ND_HOST/credentials and connectivity.",
                "query_errors": query_errors,
            })
            return result

        result.update({
            "changed": False,
            "filtered_config": filtered_config,
            "missing_or_mismatch": missing_or_mismatch,
            "query_errors": query_errors,
            "matched_total": matched_count,
            "filtered_total": len(filtered_config),
            "desired_total": len(desired_config),
        })

        return result

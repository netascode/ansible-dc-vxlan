import os

import yaml


_REGISTRY_CACHE = None


def _load_registry():
    """Load the policy_json_params registry relative to this rule file."""
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is None:
        here = os.path.dirname(os.path.abspath(__file__))
        # here: roles/validate/files/rules/common -> collection root is 5 levels up
        collection_root = os.path.abspath(os.path.join(here, "..", "..", "..", "..", ".."))
        registry_path = os.path.join(collection_root, "resources", "policy_json_params.yml")
        with open(registry_path, "r") as handle:
            _REGISTRY_CACHE = yaml.safe_load(handle) or {}
    return _REGISTRY_CACHE


def _resolve_template_vars(pol):
    """Return the policy's template_vars, loading them from an external
    `filename` (.yml/.yaml) per the NaC file convention when present. Read-only:
    the data model is never mutated during validation."""
    template_vars = pol.get("template_vars")
    if isinstance(template_vars, dict):
        return template_vars

    filename = pol.get("filename")
    if isinstance(filename, str) and filename.lower().endswith((".yml", ".yaml")):
        try:
            with open(os.path.expanduser(filename), "r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle) or {}
        except OSError:
            return None
        if isinstance(loaded, dict):
            return loaded
    return None


class Rule:
    id = "550"
    description = "Validate structured JSON-encoded policy template_vars against the policy_json_params registry"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []

        policy = (data_model.get("vxlan") or {}).get("policy") or {}
        policies = policy.get("policies") or []
        if not policies:
            return results

        registry = _load_registry()

        for pol in policies:
            spec = registry.get(pol.get("template_name"))
            if not spec:
                continue

            template_vars = _resolve_template_vars(pol)
            if not isinstance(template_vars, dict):
                continue

            name = pol.get("name")
            for param in spec.get("json_params", []):
                key = param["key"]
                value = template_vars.get(key)

                # Absent, or a raw JSON string the user supplied directly: not validated here.
                if value is None or isinstance(value, str):
                    continue

                if not isinstance(value, list):
                    results.append(
                        f"Policy '{name}' template_vars.{key} must be a list of entries or a JSON string."
                    )
                    continue

                cls._validate_entries(
                    results, name, key, value, param["fields"], param.get("required", [])
                )

        return results

    @classmethod
    def _validate_entries(cls, results, name, path, entries, fields, required):
        """Validate a structureArray (list of entries) against its field specs,
        recursing into nested structureArrays."""
        allowed = set(fields.keys())
        required = set(required)

        for idx, entry in enumerate(entries):
            loc = f"{path}[{idx}]"
            if not isinstance(entry, dict):
                results.append(f"Policy '{name}' {loc} must be a mapping.")
                continue

            unknown = set(entry.keys()) - allowed
            if unknown:
                results.append(
                    f"Policy '{name}' {loc} has unknown field(s): "
                    f"{sorted(unknown)}. Allowed: {sorted(allowed)}"
                )

            missing = required - set(entry.keys())
            if missing:
                results.append(
                    f"Policy '{name}' {loc} missing required field(s): {sorted(missing)}"
                )

            for field_name, field_value in entry.items():
                field_spec = fields.get(field_name)
                if not isinstance(field_spec, dict):
                    continue

                field_type = field_spec.get("type")

                if field_type == "structure_array":
                    if field_value is None:
                        continue
                    if not isinstance(field_value, list):
                        results.append(
                            f"Policy '{name}' {loc}.{field_name} must be a list of entries."
                        )
                        continue
                    cls._validate_entries(
                        results, name, f"{loc}.{field_name}", field_value,
                        field_spec["fields"], field_spec.get("required", []),
                    )
                    continue

                if field_type == "list":
                    if field_value is not None and not isinstance(field_value, list):
                        results.append(
                            f"Policy '{name}' {loc}.{field_name} must be a list."
                        )
                    continue

                allowed_values = field_spec.get("enum")
                if allowed_values and str(field_value) not in {str(a) for a in allowed_values}:
                    results.append(
                        f"Policy '{name}' {loc}.{field_name}='{field_value}' "
                        f"is not one of {allowed_values}"
                    )

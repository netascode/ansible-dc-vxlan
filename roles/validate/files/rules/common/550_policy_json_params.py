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

            template_vars = pol.get("template_vars")
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

                allowed = set(param["fields"].keys())
                required = set(param.get("required", []))

                for idx, entry in enumerate(value):
                    if not isinstance(entry, dict):
                        results.append(f"Policy '{name}' {key}[{idx}] must be a mapping.")
                        continue

                    unknown = set(entry.keys()) - allowed
                    if unknown:
                        results.append(
                            f"Policy '{name}' {key}[{idx}] has unknown field(s): "
                            f"{sorted(unknown)}. Allowed: {sorted(allowed)}"
                        )

                    missing = required - set(entry.keys())
                    if missing:
                        results.append(
                            f"Policy '{name}' {key}[{idx}] missing required field(s): {sorted(missing)}"
                        )

                    for field_name, field_value in entry.items():
                        field_spec = param["fields"].get(field_name)
                        if not isinstance(field_spec, dict):
                            continue
                        allowed_values = field_spec.get("enum")
                        if allowed_values and field_value not in allowed_values:
                            results.append(
                                f"Policy '{name}' {key}[{idx}].{field_name}='{field_value}' "
                                f"is not one of {allowed_values}"
                            )

        return results

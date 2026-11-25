import os
import re

import yaml
import yamale
from yamale.validators import Any as AnyValidator, DefaultValidators, Enum, Include, Ip, List, Regex, String


_REGISTRY_CACHE = None
_SCHEMA_CACHE = None
_ENV_VAR_TOKEN = re.compile(r"env_var_\w+")


def _resource_path(name):
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", "..", "..", "..", ".."))
    return os.path.join(root, "resources", name)


def _load_registry():
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is None:
        with open(_resource_path("policy_json_params.yml"), "r", encoding="utf-8") as handle:
            _REGISTRY_CACHE = yaml.safe_load(handle)
    return _REGISTRY_CACHE


def _placeholder_validator(native):
    class Scalar(native):
        def validate(self, value):
            if isinstance(value, str) and _ENV_VAR_TOKEN.search(value):
                return []
            return super().validate(value)

    return Scalar


def _schema_validators():
    validators = dict(DefaultValidators)
    for tag in ("str", "int", "bool", "enum", "ip", "mac"):
        validators[tag] = _placeholder_validator(validators[tag])
    return validators


def _load_schema():
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        _SCHEMA_CACHE = yamale.make_schema(
            _resource_path("policy_json_params_schema.yml"), validators=_schema_validators()
        )
    return _SCHEMA_CACHE


def _resolve_template_vars(pol):
    value = pol.get("template_vars")
    if isinstance(value, dict):
        return value
    filename = pol.get("filename")
    if isinstance(filename, str) and filename.lower().endswith((".yml", ".yaml")):
        with open(os.path.expanduser(filename), "r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
        return {} if loaded is None else loaded
    return value


def _is_empty(value):
    return value is None or value == [] or (isinstance(value, str) and not value.strip())


def _prepare(value, validator, schema, path, hints, errors, alternatives):
    """Adapt a validation-only copy; Yamale owns the actual schema checks."""
    hint = validator.kwargs.get("desc")
    if hint:
        hints[path] = hint
    if isinstance(value, str) and _ENV_VAR_TOKEN.search(value):
        return [value] if validator.kwargs.get("nd_type") == "ipaddresslist" else value
    if validator.kwargs.get("nd_type") == "ipaddresslist" and isinstance(value, str):
        value = [item.strip() for item in value.split(",")]
    if isinstance(validator, AnyValidator):
        choices = validator.validators
        selected = next((v for v in choices if isinstance(v, List)), choices[0]) if isinstance(value, list) else choices[0]
        prepared = _prepare(value, selected, schema, path, hints, errors, alternatives)
        # The remaining any() is the list/raw-string compatibility union.
        # Suppress failures from its deliberately inapplicable branch.
        alternatives.extend(f"{path}: {error}" for other in choices if other is not selected
                            for error in other.validate(prepared))
        return prepared
    if isinstance(validator, Include) and isinstance(value, dict):
        fields = schema.includes[validator.include_name].dict
        return {
            key: _prepare(item, fields[key], schema, f"{path}.{key}", hints, errors, alternatives) if key in fields else item
            for key, item in value.items()
            if key not in fields or not _is_empty(item)
        }
    if isinstance(validator, List) and isinstance(value, list):
        return [_prepare(item, validator.validators[0], schema, f"{path}.{index}", hints, errors, alternatives)
                for index, item in enumerate(value)]
    if isinstance(validator, Enum) and isinstance(value, (str, bool, int, float)):
        return str(value).lower() if isinstance(value, bool) else str(value)
    if isinstance(validator, (String, Regex, Ip)) and isinstance(value, int) and not isinstance(value, bool):
        value = str(value)
    if isinstance(validator, Ip) and isinstance(value, str) and not validator.validate(value):
        # Yamale ip() accepts both addresses and interfaces. ND distinguishes them.
        kind = validator.kwargs.get("nd_type", "")
        prefix_required = "withsubnet" in kind or "withprefix" in kind
        if kind and ("/" in value) != prefix_required:
            expected = "an IP address with a prefix length" if prefix_required else "an IP address without a prefix"
            errors.append(f"{path}: expected {expected}.")
    return value


def _message(name, template, error, hints):
    path, separator, reason = error.partition(": ")
    hint = hints.get(path)
    if path == template:
        path = "template_vars"
    elif path.startswith(template + "."):
        path = "template_vars" + path[len(template):]
    path = re.sub(r"\.(\d+)(?=\.|$)", r"[\1]", path)
    message = f"Policy '{name}' {path}{separator}{reason}"
    return message + (f" Expected: {hint}" if hint else "")


class Rule:
    id = "550"
    description = "Validate JSON-encoded policy template_vars with the generated Yamale schema"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        policies = ((data_model.get("vxlan") or {}).get("policy") or {}).get("policies") or []
        if not policies:
            return results
        try:
            registry = _load_registry()
            schema = _load_schema()
        except (OSError, ValueError, yaml.YAMLError) as exc:
            return [f"Rule 550 could not load its policy registry/schema: {exc}"]
        if not isinstance(registry, dict):
            return ["Rule 550 policy_json_params.yml must contain a template mapping."]

        for pol in policies:
            template = pol.get("template_name")
            spec = registry.get(template)
            if spec is None:
                continue
            if template not in schema.dict:
                results.append(f"Rule 550 has no Yamale schema for registered template '{template}'.")
                continue
            try:
                variables = _resolve_template_vars(pol)
            except (OSError, yaml.YAMLError) as exc:
                results.append(f"Policy '{pol.get('name')}' could not read YAML filename '{pol.get('filename')}' ({type(exc).__name__}).")
                continue
            if variables is None:
                if pol.get("filename"):
                    continue
                variables = {}
            if not isinstance(variables, dict):
                results.append(f"Policy '{pol.get('name')}' template_vars must be a mapping.")
                continue
            keys = {param["key"] for param in spec["json_params"]}
            desired = {key: value for key, value in variables.items() if key in keys}
            hints, errors, alternatives = {}, [], []
            prepared = _prepare(desired, schema.dict[template], schema, template, hints, errors, alternatives)
            try:
                yamale.validate(schema, [({template: prepared}, pol.get("name"))], strict=True)
            except yamale.YamaleError as exc:
                errors.extend(error for result in exc.results for error in result.errors)
            for message in alternatives:
                if message in errors:
                    errors.remove(message)
            results.extend(_message(pol.get("name"), template, error, hints) for error in errors)
        return results

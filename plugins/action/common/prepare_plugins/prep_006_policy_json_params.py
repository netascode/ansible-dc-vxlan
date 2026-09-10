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

import json
import os

import yaml

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.registry_loader import RegistryLoader


class PreparePlugin:
    """
    Encode structured policy template_vars into the JSON strings NDFC expects.

    Users may author NDFC "structureArray" nvPairs (e.g. ip_acl ACES) as native
    YAML lists of dicts. This plugin looks each policy up in the
    policy_json_params registry and, for any declared param whose value is a
    list, rewrites it into the '{"<wrapper_key>": [ {NDFC_FIELD: "value"} ]}'
    JSON string. Values already supplied as strings are left untouched.

    Structured vars may also be authored in an external file via the NaC
    `filename` convention; a .yml/.yaml file for a registered template is loaded
    into template_vars before encoding. Field specs are recursive, so nested
    structureArrays (e.g. route_map_enhanced entries -> rule_entries) and scalar
    lists are supported.
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.keys = []

    def prepare(self):
        data_model = self.kwargs['results']['model_extended']

        policy = (data_model.get('vxlan') or {}).get('policy')
        if not policy or not policy.get('policies'):
            return self.kwargs['results']

        registry = RegistryLoader.load(RegistryLoader.get_collection_path(), 'policy_json_params')

        for pol in policy['policies']:
            spec = registry.get(pol.get('template_name'))
            if not spec:
                continue

            template_vars = self._resolve_template_vars(pol)
            if not isinstance(template_vars, dict):
                continue

            for param in spec.get('json_params', []):
                key = param['key']
                value = template_vars.get(key)
                # Only encode structured input; a raw JSON string is passed through.
                if not isinstance(value, list):
                    continue

                wrapper_key = param.get('wrapper_key', key)
                encoded_items = self._encode_items(value, param['fields'])
                template_vars[key] = json.dumps({wrapper_key: encoded_items}, separators=(",", ":"))

        self.kwargs['results']['model_extended'] = data_model

        return self.kwargs['results']

    @staticmethod
    def _resolve_template_vars(pol):
        """Return the policy's template_vars, loading them from an external
        `filename` (.yml/.yaml) per the NaC file convention when the vars live
        in a file. Non-YAML files (e.g. .cfg) are left for the template layer."""
        template_vars = pol.get('template_vars')
        if isinstance(template_vars, dict):
            return template_vars

        filename = pol.get('filename')
        if isinstance(filename, str) and filename.lower().endswith((".yml", ".yaml")):
            with open(os.path.expanduser(filename), 'r', encoding='utf-8') as handle:
                loaded = yaml.safe_load(handle) or {}
            if isinstance(loaded, dict):
                pol['template_vars'] = loaded
                pol.pop('filename', None)
                return loaded
        return template_vars

    @classmethod
    def _encode_items(cls, entries, fields):
        """Encode a structureArray: a list of entries -> list of NDFC nvPair dicts."""
        encoded = []
        for entry in entries or []:
            entry = entry or {}
            row = {}
            for snake_name, field_spec in fields.items():
                ndfc_name, cell = cls._encode_field(field_spec, entry.get(snake_name))
                row[ndfc_name] = cell
            encoded.append(row)
        return encoded

    @classmethod
    def _encode_field(cls, field_spec, value):
        """Encode one field into (ndfc_name, nvPair_value)."""
        # Simple field: the value is just the NDFC nvPair name.
        if isinstance(field_spec, str):
            return field_spec, cls._scalar(value)

        ndfc_name = field_spec['ndfc']
        field_type = field_spec.get('type')

        # Nested structureArray: recurse, then wrap like a top-level structureArray.
        if field_type == 'structure_array':
            sub_items = cls._encode_items(value if isinstance(value, list) else [], field_spec['fields'])
            wrapper = field_spec.get('wrapper_key', ndfc_name)
            return ndfc_name, cls._maybe_stringify(field_spec, {wrapper: sub_items})

        # Scalar list (e.g. prefix_list_names): JSON array of string values.
        if field_type == 'list':
            if isinstance(value, list):
                vals = value
            elif value in (None, ""):
                vals = []
            else:
                vals = [value]
            return ndfc_name, cls._maybe_stringify(field_spec, [cls._scalar(v) for v in vals])

        # Plain scalar (an accompanying enum is validation-only).
        return ndfc_name, cls._scalar(value)

    @staticmethod
    def _maybe_stringify(field_spec, payload):
        """NDFC nvPair values are strings, so complex fields are JSON-stringified
        by default. Set `stringify: false` to embed an inline nested JSON value."""
        if field_spec.get('stringify', True):
            return json.dumps(payload, separators=(",", ":"))
        return payload

    @staticmethod
    def _scalar(value):
        if isinstance(value, bool):
            # NDFC nvPairs use lowercase JSON booleans.
            return "true" if value else "false"
        return "" if value is None else str(value)

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

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.registry_loader import RegistryLoader


class PreparePlugin:
    """
    Encode structured policy template_vars into the JSON strings NDFC expects.

    Users may author NDFC "structureArray" nvPairs (e.g. ip_acl ACES) as native
    YAML lists of dicts. This plugin looks each policy up in the
    policy_json_params registry and, for any declared param whose value is a
    list, rewrites it into the '{"<wrapper_key>": [ {NDFC_FIELD: "value"} ]}'
    JSON string. Values already supplied as strings are left untouched.
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

            template_vars = pol.get('template_vars')
            if not isinstance(template_vars, dict):
                continue

            for param in spec.get('json_params', []):
                key = param['key']
                value = template_vars.get(key)
                # Only encode structured input; a raw JSON string is passed through.
                if not isinstance(value, list):
                    continue

                fields = param['fields']
                wrapper_key = param.get('wrapper_key', key)

                encoded_items = []
                for entry in value:
                    entry = entry or {}
                    row = {}
                    for snake_name, field_spec in fields.items():
                        # field_spec is either the NDFC name (str) or {ndfc, enum}.
                        ndfc_name = field_spec if isinstance(field_spec, str) else field_spec['ndfc']
                        cell = entry.get(snake_name, "")
                        row[ndfc_name] = "" if cell is None else str(cell)
                    encoded_items.append(row)

                template_vars[key] = json.dumps({wrapper_key: encoded_items}, separators=(",", ":"))

        self.kwargs['results']['model_extended'] = data_model

        return self.kwargs['results']

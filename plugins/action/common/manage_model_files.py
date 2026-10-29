# Copyright (c) 2024 Cisco Systems, Inc. and its affiliates
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

from __future__ import absolute_import, division, print_function


__metaclass__ = type

import difflib
import json
import os
import stat
import tempfile

from ansible.plugins.action import ActionBase
from ansible.parsing.ajson import AnsibleJSONEncoder
from ansible.errors import AnsibleActionFail
from ansible.utils.display import Display

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.helper_functions import resolve_files_root

display = Display()

MAX_DIFF_LINES = 2000


def serialize_model(model):
    # Must stay byte-identical to the `to_nice_json` filter: indent=4, sorted
    # keys, ',' / ': ' separators, no trailing newline. Any drift makes an
    # unchanged model hash differently and report a false "changed".
    text = json.dumps(
        model,
        indent=4,
        sort_keys=True,
        separators=(',', ': '),
        cls=AnsibleJSONEncoder,
    )
    return text.encode('utf-8')


def read_file_bytes(path):
    try:
        with open(path, 'rb') as file_handle:
            return file_handle.read()
    except (OSError, IOError):
        return None


def existing_mode(path, default=0o600):
    try:
        return stat.S_IMODE(os.stat(path).st_mode)
    except OSError:
        return default


def atomic_write(path, data, mode):
    directory = os.path.dirname(path) or '.'
    file_descriptor, temp_path = tempfile.mkstemp(dir=directory, prefix='.smd_', suffix='.tmp')
    try:
        with os.fdopen(file_descriptor, 'wb') as file_handle:
            file_handle.write(data)
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
    except Exception:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise


_MISSING = object()


def _path_key(path, key):
    if isinstance(key, str) and key.isidentifier():
        return "{0}.{1}".format(path, key)
    return "{0}[{1}]".format(path, json.dumps(key, cls=AnsibleJSONEncoder))


def _named_items(value):
    if not value or not all(isinstance(item, dict) and item.get('name') is not None for item in value):
        return None
    names = [str(item['name']) for item in value]
    if len(names) != len(set(names)):
        return None
    return dict(zip(names, value))


def _value_text(value):
    return json.dumps(value, sort_keys=True, cls=AnsibleJSONEncoder)


def _missing_diff(value, path, prefix):
    if isinstance(value, dict):
        if not value:
            yield '{0} {1} = {{}}'.format(prefix, path)
        for key in sorted(value, key=str):
            yield from _missing_diff(value[key], _path_key(path, key), prefix)
        return
    if isinstance(value, list):
        if not value:
            yield '{0} {1} = []'.format(prefix, path)
            return
        named = _named_items(value)
        if named is not None:
            for name in sorted(named):
                item_path = '{0}[name={1}]'.format(path, json.dumps(name))
                yield from _missing_diff(named[name], item_path, prefix)
        else:
            for index, item in enumerate(value):
                yield from _missing_diff(item, '{0}[{1}]'.format(path, index), prefix)
        return
    yield '{0} {1} = {2}'.format(prefix, path, _value_text(value))


def _model_diff(before, after, path='$'):
    if before is _MISSING:
        yield from _missing_diff(after, path, '+')
        return
    if after is _MISSING:
        yield from _missing_diff(before, path, '-')
        return
    if before == after:
        return

    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after), key=str):
            yield from _model_diff(
                before.get(key, _MISSING),
                after.get(key, _MISSING),
                _path_key(path, key),
            )
        return

    if isinstance(before, list) and isinstance(after, list):
        before_named = _named_items(before)
        after_named = _named_items(after)
        named_comparison = (
            (before_named is not None and (after_named is not None or not after))
            or (after_named is not None and (before_named is not None or not before))
        )
        if named_comparison:
            before_named = before_named or {}
            after_named = after_named or {}
            before_order = [str(item['name']) for item in before]
            after_order = [str(item['name']) for item in after]
            if set(before_named) == set(after_named) and before_order != after_order:
                mismatch = next((
                    index
                    for index in range(min(len(before_order), len(after_order)))
                    if before_order[index] != after_order[index]
                ), min(len(before_order), len(after_order)))
                before_name = before_order[mismatch] if mismatch < len(before_order) else None
                after_name = after_order[mismatch] if mismatch < len(after_order) else None
                yield '- {0}.order[{1}] = {2}'.format(
                    path, mismatch, _value_text(before_name)
                )
                yield '+ {0}.order[{1}] = {2}'.format(
                    path, mismatch, _value_text(after_name)
                )
            for name in sorted(set(before_named) | set(after_named)):
                item_path = '{0}[name={1}]'.format(path, json.dumps(name))
                yield from _model_diff(
                    before_named.get(name, _MISSING),
                    after_named.get(name, _MISSING),
                    item_path,
                )
        else:
            for index in range(max(len(before), len(after))):
                yield from _model_diff(
                    before[index] if index < len(before) else _MISSING,
                    after[index] if index < len(after) else _MISSING,
                    '{0}[{1}]'.format(path, index),
                )
        return

    if isinstance(before, (dict, list)) or isinstance(after, (dict, list)):
        yield from _missing_diff(before, path, '-')
        yield from _missing_diff(after, path, '+')
        return

    yield '- {0} = {1}'.format(path, _value_text(before))
    yield '+ {0} = {1}'.format(path, _value_text(after))


def _bounded_lines(lines):
    output = []
    for line in lines:
        if len(output) == MAX_DIFF_LINES:
            output.append('... diff truncated at {0} lines ...'.format(MAX_DIFF_LINES))
            break
        output.append(line)
    return output


def render_diff(*, old_bytes, new_bytes):
    before_text = old_bytes.decode('utf-8')
    after_text = new_bytes.decode('utf-8')
    try:
        return _bounded_lines(_model_diff(json.loads(before_text), json.loads(after_text)))
    except ValueError:
        return _bounded_lines(difflib.unified_diff(
            before_text.splitlines(),
            after_text.splitlines(),
            fromfile='previous',
            tofile='current',
            n=2,
            lineterm='',
        ))


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        task_vars = task_vars or {}

        model_dir = resolve_files_root(task_vars, 'validate', self._templar)
        fabric_name = self._task.args['fabric_name']
        checksum_compare = bool(self._task.args.get('checksum_compare_enabled', False))
        diff_enabled = bool(self._task.args.get('diff_enabled', False))
        save_previous = bool(self._task.args.get('save_previous', True))

        golden_model = task_vars.get('data_model')
        extended_model = task_vars.get('data_model_extended')
        if golden_model is None or extended_model is None:
            raise AnsibleActionFail(
                "manage_model_files requires 'data_model' and 'data_model_extended' facts to be set"
            )

        paths = {
            'golden': os.path.join(model_dir, "{0}_service_model_golden.json".format(fabric_name)),
            'extended': os.path.join(model_dir, "{0}_service_model_extended.json".format(fabric_name)),
        }
        new_bytes = {
            'golden': serialize_model(golden_model),
            'extended': serialize_model(extended_model),
        }
        old_bytes = {key: read_file_bytes(path) for key, path in paths.items()}

        unchanged = all(old_bytes[key] == new_bytes[key] for key in paths)

        if checksum_compare and unchanged:
            results['changed'] = False
            results['end_host'] = True
            return results

        if diff_enabled:
            for key, path in paths.items():
                if old_bytes[key] is None or old_bytes[key] == new_bytes[key]:
                    continue
                diff_lines = render_diff(old_bytes=old_bytes[key], new_bytes=new_bytes[key])
                if diff_lines:
                    display.display("Service model changes for {0}:".format(os.path.basename(path)))
                    display.display("\n".join(diff_lines))

        for key, path in paths.items():
            mode = existing_mode(path)
            if save_previous and os.path.exists(path):
                os.replace(path, path[:-len('.json')] + '_previous.json')
            atomic_write(path, new_bytes[key], mode)

        results['changed'] = not unchanged
        results['end_host'] = False
        return results

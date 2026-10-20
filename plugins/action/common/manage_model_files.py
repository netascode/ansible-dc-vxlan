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

import json
import os
import stat
import tempfile

from collections import Counter

from ansible.plugins.action import ActionBase
from ansible.parsing.ajson import AnsibleJSONEncoder
from ansible.errors import AnsibleActionFail
from ansible.utils.display import Display

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


def existing_mode(path, default=0o644):
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


def render_diff(old_bytes, new_bytes):
    before = old_bytes.decode('utf-8').splitlines()
    after = new_bytes.decode('utf-8').splitlines()
    removed = list((Counter(before) - Counter(after)).elements())
    added = list((Counter(after) - Counter(before)).elements())
    lines = ['- ' + text for text in removed[:MAX_DIFF_LINES]]
    lines += ['+ ' + text for text in added[:MAX_DIFF_LINES]]
    if len(removed) > MAX_DIFF_LINES or len(added) > MAX_DIFF_LINES:
        lines.append('... diff truncated at {0} lines per side ...'.format(MAX_DIFF_LINES))
    return lines


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        task_vars = task_vars or {}

        model_dir = self._task.args['model_dir']
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
                diff_lines = render_diff(old_bytes[key], new_bytes[key])
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

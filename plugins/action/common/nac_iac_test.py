from __future__ import absolute_import, division, print_function


__metaclass__ = type

from ansible import constants as C
from ansible.utils.display import Display
from ansible.plugins.action import ActionBase

import os
import iac_test.robot_writer
import iac_test.pabot

display = Display()

class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False
        results['msg'] = None

        data = self._task.args.get('data')
        templates = self._task.args.get('templates')
        filters = self._task.args.get('filters', "")
        tests = self._task.args.get('tests', "")
        output = self._task.args.get('output')
        include = self._task.args.get('include', [])
        exclude = self._task.args.get('exclude', [])
        render_only = self._task.args.get('render_only', "")
        dry_run = self._task.args.get('dry_run', "")

        if output and not os.path.exists(output):
            display.warning(f"The provided directory {output} does not appear to exist. Is it a directory?")

        writer = iac_test.robot_writer.RobotWriter(data, filters, tests, include, exclude)
        writer.write(templates, output)
        if not render_only:
            iac_test.pabot.run_pabot(output, include, exclude, dry_run)

        results["changed"] = True

        return results

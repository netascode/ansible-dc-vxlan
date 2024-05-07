from __future__ import absolute_import, division, print_function


__metaclass__ = type

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False

        test_data = self._task.args['test_data']['response']

        if len(test_data) != 7:
            results['msg'] = 'There should be 7 switches in the fabric but only found %d' % len(test_data)
            results['failed'] = True

        return results

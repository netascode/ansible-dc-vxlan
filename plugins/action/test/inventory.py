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
        model_data = self._task.args['model_data']

        num_fabric_devices = len(test_data)
        num_model_devices = len(model_data['vxlan']['topology']['switches'])
        if num_fabric_devices != num_model_devices:
            results['msg'] = 'There should be {0} switches in the fabric but only found {1}'.format(num_model_devices, num_fabric_devices)
            results['failed'] = True

        return results

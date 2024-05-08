from __future__ import absolute_import, division, print_function


__metaclass__ = type

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        # self._supports_async = True
        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False

        fabric_data = self._task.args['fabric_data']

        if fabric_data.get('global').get('auth_proto') is None:
            results['failed'] = True
            results['msg'] = "Data model path 'vxlan.global.auth_proto' must be defined!"
            return results

        if fabric_data.get('topology').get('switches') is not None:
            for switch in fabric_data['topology']['switches']:
                for key in ['management', 'role']:
                    if switch.get(key) is None:
                        results['failed'] = True
                        results['msg'] = "Data model path 'vxlan.topology.switches.{0}.{1}' must be defined!".format(switch['name'], key)
                        return results

        return results

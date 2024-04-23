from __future__ import absolute_import, division, print_function


__metaclass__ = type

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        # self._supports_async = True
        results = super(ActionModule, self).run(tmp, task_vars)
        results['save_previous'] = False

        roles = self._task.args['role_list']
        for role in ['cisco.nac_dc_vxlan.create', 'cisco.nac_dc_vxlan.remove']:
            if role in roles:
                results['save_previous'] = True

        return results

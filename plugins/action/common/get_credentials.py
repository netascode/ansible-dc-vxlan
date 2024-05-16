from __future__ import absolute_import, division, print_function


__metaclass__ = type

from ansible.utils.display import Display
from ansible.plugins.action import ActionBase
import ansible.plugins.lookup.env
from ansible.plugins.loader import lookup_loader

import copy

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        # self._supports_async = True
        # import epdb; epdb.set_trace()

        # task_vars.get('ndfc_switch_username')

        lookup = lookup_loader.get('ansible.builtin.env')
        username = lookup.run(['NDFC_SWITCH_USER'], task_vars, default='admin')

        results = super(ActionModule, self).run(tmp, task_vars)
        results['failed'] = False

        inv_list = self._task.args['inv_list']
        username = task_vars.get('ndfc_switch_username')
        password = task_vars.get('ndfc_switch_password')

        # Fail if username and password are not set
        if username is None or password is None:
            results['failed'] = True
            results['msg'] = "ndfc_switch_username and ndfc_switch_password must be set in group_vars or as environment variables!"
            # TODO: Add support for environemnt variables
            return results

        # Create a new list and deep copy each dict item to avoid modifying the original and dict items
        updated_inv_list = []
        for device in inv_list:
            updated_inv_list.append(copy.deepcopy(device))

        for new_device in updated_inv_list:
            new_device['user_name'] = username
            new_device['password'] = password

        results['updated_inv_list'] = updated_inv_list
        return results

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

        inv_config = self._task.args['inv_config']
        username = task_vars.get('ndfc_device_username')
        password = task_vars.get('ndfc_device_password')

        # Fail if username and password are not set
        if username is None or password is None:
            results['failed'] = True
            results['msg'] = "ndfc_device_username and ndfc_device_username must be set in group_vars or as environment variables!"
            # TODO: Add support for environemnt variables
            return results

        # Loop through inv_config and update username and password
        for device in inv_config:
            device['user_name'] = username
            device['password'] = password

        results['inv_config'] = inv_config
        return results
from __future__ import absolute_import, division, print_function


__metaclass__ = type

from ansible import constants as C
from ansible.utils.display import Display
from ansible.plugins.action import ActionBase

from ..helper_functions import do_something

from pprint import pprint

display = Display()

class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        # self._supports_async = True
        results = super(ActionModule, self).run(tmp, task_vars)
        results['exists'] = False

        fabric_data = self._task.args['fabric_data']['response']['DATA']
        fabric_name = self._task.args['fabric_name']

        for fabric in fabric_data:
            if fabric['fabricName'] == fabric_name:
                display.warning("Fabric name ({0}) already exists on NDFC".format(fabric['fabricName']))
                results['exists'] = True

        if not results['exists']:
            display.warning("Fabric name ({0}) does NOT exist on NDFC".format(fabric_name))

        return results
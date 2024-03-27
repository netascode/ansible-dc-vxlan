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
        results['failed'] = False

        vpc_data = self._task.args['vpc_data']

        vpc_pairs = {}
        pair = 1
        # The following for loop creates a dictionary (vpc_pairs) that looks like this:
        #  {
        #    1: {'netascode-rtp-leaf1': False, 'netascode-rtp-leaf2': False},
        #    2: {'netascode-rtp-leaf3': False, 'netascode-rtp-leaf4': False}
        #  }
        for switch_pair in vpc_data['results']:
            vpc_pairs[pair] = {}
            for switch in switch_pair['response']:
                if not switch['isVpcConfigured']:
                    name = switch['hostName']
                    vpc_pairs[pair][name] = False
            pair += 1

        # vpc_data['results'][0]['response'][0]['isVpcConfigured']
        # vpc_data['results'][0]['response'][1]['isVpcConfigured']
        # vpc_data['results'][1]['response'][0]['isVpcConfigured']
        # vpc_data['results'][1]['response'][1]['isVpcConfigured']


        if fabric_data.get('global').get('auth_proto') is None:
            results['failed'] = True
            results['msg'] = "Data model path 'fabric.global.auth_proto' must be defined!"
            return results

        if fabric_data.get('topology').get('switches') is not None:
            for switch in fabric_data['topology']['switches']:
                for key in ['management', 'role']:
                    if switch.get(key) is None:
                        results['failed'] = True
                        results['msg'] = "Data model path 'fabric.topology.switches.{0}.{1}' must be defined!".format(switch['name'],key)
                        return results

        return results
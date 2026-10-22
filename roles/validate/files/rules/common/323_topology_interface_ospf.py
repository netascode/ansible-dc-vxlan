class Rule:
    id = "323"
    description = "Verify OSPF configuration: sub-fields require enable_ospf; MD5 auth fields require enable_ospf_auth; auth mechanisms are mutually exclusive"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        switches_check = cls.data_model_key_check(data_model, ['vxlan', 'topology', 'switches'])
        if 'switches' not in switches_check['keys_data']:
            return results

        # Fields that require enable_ospf=true
        ospf_sub_fields = [
            'ospf_tag', 'ospf_area_id',
            'enable_ospf_auth', 'ospf_auth_key_id', 'ospf_auth_key',
            'ospf_authentication_key_type', 'ospf_authentication_key',
            'ospf_passive_mode', 'ospf_cost', 'ospf_mtu_ignore',
            'ospf_hello_interval', 'ospf_dead_interval', 'ospf_shutdown',
            'ospf_transmit_delay', 'ospf_priority', 'ospf_network_type',
            'ospf_bfd_mode',
        ]
        # MD5 auth fields (require enable_ospf_auth=true)
        md5_auth_fields = ['ospf_auth_key_id', 'ospf_auth_key']

        switches = data_model['vxlan']['topology']['switches']
        for switch in switches:
            for interface in switch.get('interfaces', []):
                enable_ospf = interface.get('enable_ospf', None)
                enable_ospf_auth = interface.get('enable_ospf_auth', None)

                # Check 1: OSPF sub-fields require enable_ospf=true
                sub_set = [f for f in ospf_sub_fields if interface.get(f) is not None]
                if sub_set and enable_ospf is not True:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"OSPF sub-fields ({', '.join(sub_set)}) require "
                        f"enable_ospf=true on the same interface."
                    )

                # Check 2: MD5 auth fields require enable_ospf_auth=true
                md5_set = [f for f in md5_auth_fields if interface.get(f) is not None]
                if md5_set and enable_ospf_auth is not True:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"OSPF MD5 authentication fields ({', '.join(md5_set)}) require "
                        f"enable_ospf_auth=true on the same interface."
                    )

                # Check 3: Auth mechanism mutex (MD5 vs plain-authentication-key)
                md5_key = interface.get('ospf_auth_key')
                plain_key = interface.get('ospf_authentication_key')
                if md5_key and plain_key:
                    results.append(
                        f"For switch {switch.get('name')} "
                        f"interface {interface.get('name')} "
                        f"OSPF has two authentication mechanisms and both are configured: "
                        f"MD5 (ospf_auth_key) and plain (ospf_authentication_key). "
                        f"Configuring both results in MD5 being active while the plain key "
                        f"sits unused in running-config. Set only one mechanism."
                    )

        return results

    @classmethod
    def data_model_key_check(cls, tested_object, keys):
        dm_key_dict = {
            'keys_found': [], 'keys_not_found': [],
            'keys_data': [], 'keys_no_data': [],
        }
        for key in keys:
            if tested_object and key in tested_object:
                dm_key_dict['keys_found'].append(key)
                tested_object = tested_object[key]
                if tested_object:
                    dm_key_dict['keys_data'].append(key)
                else:
                    dm_key_dict['keys_no_data'].append(key)
            else:
                dm_key_dict['keys_not_found'].append(key)
        return dm_key_dict

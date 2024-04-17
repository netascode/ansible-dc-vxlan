# This is an example file for help functions that can be called by
# our various action plugins for common routines.
#
# For example in prepare_serice_model.py we can do the following:
#  from ..helper_functions import do_something

def data_model_key_check(tested_object, keys):
    dm_key_dict = {'keys_found': [], 'keys_not_found': [], 'keys_data': [], 'keys_no_data': []}
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

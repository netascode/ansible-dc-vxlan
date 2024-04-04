# This is an example file for help functions that can be called by
# our various action plugins for common routines.
#
# For example in prepare_serice_model.py we can do the following:
#  from ..helper_functions import do_something

def do_something():
    print('do something')


def has_keys(tested_object, keys):
   for key in keys:
      if key in tested_object:
         tested_object = tested_object[key]
      else:
         return False
   return True

	# List of keys that we found
    # List of keys we did not find
    # List of keys we found but no data under it
    # List of keys we found with data under it

Role Name
=========

The render role for Network as Code is used to create rendering templates that can be pushed into NDFC or for direct to device configuration CLI.


Requirements
------------

This module requires the validate role to load the data model into run memory.

Role Variables
--------------


Dependencies
------------

cisco.nac_dc_vxlan.validate

Example Playbook
----------------

  roles:
    # Prepare service model for all subsequent roles
    #
    - role: cisco.nac_dc_vxlan.render

License
-------

BSD

Author Information
------------------
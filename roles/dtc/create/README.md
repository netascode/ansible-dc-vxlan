Role Name: cisco.nac_dc_vxlan.dtc.create
========================================

This role is used to create and update NDFC state based on service model data changes.

Requirements
------------
None

Role Variables
--------------
None

Dependencies
------------

See [Galaxy File](https://github.com/netascode/ansible-dc-vxlan/blob/develop/galaxy.yml#L14)


Example Playbook
----------------

```yaml
  - hosts: netascode_rtpfabric

    roles:
      - role: cisco.nac_dc_vxlan.dtc.create
```

-------
The following tags can be used to selectively execute stages within the `cisco.nac_dc_vxlan.dtc.create` role

`cr` stands for `create_role`

* cr_manage_fabric
* cr_manage_switches
* cr_manage_vpc_peers
* cr_manage_interfaces
* cr_manage_vrfs_networks
* cr_manage_policy

```bash
# Selectively run stage to add VRFs and Networks and skip all other stages
ansible-playbook -i inventory.yml vxlan.yml --tags cr_manage_vrfs_networks
```

License
-------

MIT License

Copyright (c) 2024 Cisco and/or its affiliates.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

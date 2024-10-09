Role Name: cisco.nac_dc_vxlan.dtc.remove
========================================

This role is used to remove unmanaged configuration from NDFC

Requirements
------------
None

Role Variables
--------------
TODO: Update with variable to control this role (See https://github.com/netascode/ansible-dc-vxlan/issues/39)

Dependencies
------------

See [Galaxy File](https://github.com/netascode/ansible-dc-vxlan/blob/develop/galaxy.yml#L14)


Example Playbook
----------------

```yaml
  - hosts: netascode_rtpfabric

    roles:
      - role: cisco.nac_dc_vxlan.dtc.remove
```

-------
The following tags can be used to selectively execute stages within the `cisco.nac_dc_vxlan.create` role

`rr` stands for `remove_role`

* rr_manage_interfaces
* rr_manage_networks
* rr_manage_vrfs
* rr_manage_vpc_peers
* rr_manage_links
* rr_manage_switches

```bash
# Selectively run stage to remove networks and vrfs and skip all other stages
ansible-playbook -i inventory.yml vxlan.yml --tags "rr_manage_networks, rr_manage_vrfs"
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

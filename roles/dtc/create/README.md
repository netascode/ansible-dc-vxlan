Role Name
=========
cisco.nac_dc_vxlan.dtc.create

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

  - hosts: netascode_rtpfabric

    roles:
      - role: cisco.nac_dc_vxlan.dtc.create

License
-------

Copyright (c) 2024 Cisco and/or its affiliates.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
# Ansible Solution Collection:  netascode_dc_vxlan

[![Actions Status](https://github.com/netascode/ansible-dc-vxlan/workflows/CI/badge.svg)](https://github.com/netascode/ansible-dc-vxlan/actions)

Ansible collection for configuring a VXLAN Fabric using Direct to Controller (DTC) workflows.

This collection is driven by a service data model that describes the configured state of the VXLAN EVPN fabric.
Users of this collection make changes to the service model data and then use the following roles in this collection
to validate and push changes to the fabric.

### Roles

* Role: [cisco.nac_dc_vxlan.validate](https://github.com/netascode/ansible-dc-vxlan/blob/galaxy_prep/roles/validate/README.md)
* Role: [cisco.nac_dc_vxlan.dtc.create](https://github.com/netascode/ansible-dc-vxlan/blob/galaxy_prep/roles/dtc/create/README.md)
* Role: [cisco.nac_dc_vxlan.dtc.deploy](https://github.com/netascode/ansible-dc-vxlan/blob/galaxy_prep/roles/dtc/deploy/README.md)
* Role: [cisco.nac_dc_vxlan.dtc.remove](https://github.com/netascode/ansible-dc-vxlan/blob/galaxy_prep/roles/dtc/remove/README.md)


### Quick Start Guide

The following quickstart repository is available to provide a step by step guide for using this collection

[Quick Start Guide Repo](https://github.com/netascode/ansible-dc-vxlan-example)

This collection is intended for use with the following release versions:
  * `NDFC Release 12.2.1` or later.

<!--start requires_ansible-->
## Ansible version compatibility

This collection has been tested against following Ansible versions: **>=2.14.15**.

Plugins, roles and modules within a collection may be tested with only specific Ansible versions.
A collection may contain metadata that identifies these versions.
PEP440 is the schema used to describe the versions of Ansible.
<!--end requires_ansible-->

## Installing this collection

You can install the Cisco netascode_dc_vxlan collection with the Ansible Galaxy CLI:

    ansible-galaxy collection install cisco.netascode_dc_vxlan

You can also include it in a `requirements.yml` file and install it with `ansible-galaxy collection install -r requirements.yml`, using the format:

```yaml
---
collections:
  - name: cisco.netascode_dc_vxlan
    version: 0.1.0
```
## Using this collection


### Using roles from the Cisco netascode_dc_vxlan collection in your playbooks

You can call roles by their Fully Qualified Collection Namespace (FQCN), such as `cisco.netascode_dc_vxlan.validate`.

The following is a sample playbook that calls each role in this collection.

```yaml
# This is the main entry point playbook for calling the various roles in this collection.
---

- hosts: netascode_vxlan_fabric
  any_errors_fatal: true
  gather_facts: no

  vars:

  roles:
    - role: cisco.nac_dc_vxlan.validate
    - role: cisco.nac_dc_vxlan.dtc.create
    - role: cisco.nac_dc_vxlan.dtc.deploy
    - role: cisco.nac_dc_vxlan.dtc.remove
```

Sample hosts file using the dcnm httpapi connection plugin in YAML format.


```yaml
all:
  vars:
    ansible_user: "ndfc_username"
    ansible_password: "ndfc_password"
    ansible_python_interpreter: python
    ansible_httpapi_validate_certs: False
    ansible_httpapi_use_ssl: True
    ansible_httpapi_login_domain: local

  children:
    ndfc:
      children:
        netascode_vxlan_fabric:
          hosts:
            netascode_vxlan_fabric:
              ansible_host: ndfc.example.com
```

### See Also:

* [Ansible Using collections](https://docs.ansible.com/ansible/latest/user_guide/collections_using.html) for more details.

## Contributing to this collection

Ongoing development efforts and contributions to this collection are focused on new roles when needed and enhancements to current roles.

We welcome community contributions to this collection. If you find problems, please open an issue or create a PR against the [Cisco netascode_dc_vxlan collection repository](https://github.com/netascode/ansible-dc-vxlan/issues).

## Changelogs

* [Changelog](https://github.com/netascode/ansible-dc-vxlan/blob/galaxy_prep/CHANGELOG.rst)

## More information

- [NDFC installation and configuration guides](https://www.cisco.com/c/en/us/td/docs/dcn/ndfc/1201/installation/cisco-ndfc-install-and-upgrade-guide-1201.html)
- [Ansible User guide](https://docs.ansible.com/ansible/latest/user_guide/index.html)
- [Ansible Developer guide](https://docs.ansible.com/ansible/latest/dev_guide/index.html)

## Licensing

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

=============================================================
Cisco Ansible NetworkAsCode DC VXLAN Collection Release Notes
=============================================================

All notable changes to this project will be documented in this file.

This project adheres to `Semantic Versioning <http://semver.org/>`_.

.. contents:: ``Release Versions``

`0.2.0`_
=====================

**Release Date:** ``2024-06-28``

Added
-----

* Support for the following device inventory roles.  Only applies to adding devices to a fabric with these role types.
    - border_spine
    - border_gateway
    - border_gateway_spine
    - super_spine
    - border_super_spine
    - border_gateway_super_spine
* Added SysLog Server Support - Fabric Creation Stage
* Added DHCP Support and Secondary IP Address Support - Network Creation Stage
* Support for Ansible Tags
    - Tags to limit execution and target specific roles in the collection
    - Tags to limit execution and target specific stages inside a role

Fixed
-----
- https://github.com/netascode/ansible-dc-vxlan/issues/111
- https://github.com/netascode/ansible-dc-vxlan/issues/112
- https://github.com/netascode/ansible-dc-vxlan/issues/127
- https://github.com/netascode/ansible-dc-vxlan/issues/135

`0.1.0`_
=====================

**Release Date:** ``2024-06``

- Initial release of the Ansible NetworkAsCode DC VXLAN collection

Added
-----

The following roles have been added to the collection:


* Role: `cisco.nac_dc_vxlan.validate <https://github.com/netascode/ansible-dc-vxlan/blob/develop/roles/validate/README.md>`_
* Role: `cisco.nac_dc_vxlan.dtc.create <https://github.com/netascode/ansible-dc-vxlan/blob/develop/roles/dtc/create/README.md>`_
* Role: `cisco.nac_dc_vxlan.dtc.deploy <https://github.com/netascode/ansible-dc-vxlan/blob/develop/roles/dtc/deploy/README.md>`_
* Role: `cisco.nac_dc_vxlan.dtc.remove <https://github.com/netascode/ansible-dc-vxlan/blob/develop/roles/dtc/remove/README.md>`_

This version of the collection includes support for an IPv4 Underlay only.  Support for IPv6 Underlay will be available in the next release.

.. _0.2.0: https://github.com/netascode/ansible-dc-vxlan/compare/0.1.0...0.2.0
.. _0.1.0: https://github.com/netascode/ansible-dc-vxlan/compare/0.1.0...0.1.0

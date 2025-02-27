=============================================================
Cisco Ansible NetworkAsCode DC VXLAN Collection Release Notes
=============================================================

All notable changes to this project will be documented in this file.

This project adheres to `Semantic Versioning <http://semver.org/>`_.

.. contents:: ``Release Versions``

`0.4.0`_
=====================

**Release Date:** ``2025-02-28``

Added
-----

* NEW Feature: Support for data model defined policy based VRF-LITE
* NEW Feature: Support for data model defined policy based Route-Control
* NEW Feature: Support for Multi-Site Domain (MSD)
    * Support for VXLAN Child Fabric
    * Support for ISN Child Fabric
    * Support for MSD Parent Fabric
    * Support for new multisite child fabric, vrf and network delete mode protection flags
* NEW Feature: Support for managing inter-fabric links and External fabrics with ansible tag support to limit execution
* Enhanced data model validation and preprocessing
* Added new model keys for defining fabric ``name`` and ``type``

Example:

.. code-block:: yaml

    vxlan:
        fabric:
            name: nac-fabric1
            type: VXLAN_EVPN
        global:
            # name: nac-fabric1
            # fabric_type: VXLAN_EVPN


The ``name`` and ``fabric` keys under ``vxlan.global`` are still supported but will be deprecated in future releases.

Modified
--------

* Updated model key ``vxlan.overlay_services`` to be ``vxlan.overlay`` (backwards compatible)

Fixed
-----

* https://github.com/netascode/ansible-dc-vxlan/issues/234
* https://github.com/netascode/ansible-dc-vxlan/issues/235
* https://github.com/netascode/ansible-dc-vxlan/issues/236
* https://github.com/netascode/ansible-dc-vxlan/issues/237
* https://github.com/netascode/ansible-dc-vxlan/issues/243
* https://github.com/netascode/ansible-dc-vxlan/issues/246
* https://github.com/netascode/ansible-dc-vxlan/issues/252
* https://github.com/netascode/ansible-dc-vxlan/issues/253
* https://github.com/netascode/ansible-dc-vxlan/issues/256
* https://github.com/netascode/ansible-dc-vxlan/issues/259
* https://github.com/netascode/ansible-dc-vxlan/issues/265
* https://github.com/netascode/ansible-dc-vxlan/issues/270
* https://github.com/netascode/ansible-dc-vxlan/issues/272
* https://github.com/netascode/ansible-dc-vxlan/issues/276


`0.3.0`_
=====================

**Release Date:** ``2024-11-12``

Added
-----

* Support for selective execution based on data model changes
* Support for defining custom default values for data model
* Support for defining custom NDFC Policies
* Performance improvements for adding devices to a fabric
* Support for POAP when adding devices to a fabric
* New connectivity_check role for verifying connectivity and authentication to NDFC
* Updated tag support to include the following tags:
    - cc_verify
    - cr_manage_policy
    - rr_manage_policy
* Update to service model keys:
    - VRF `attach_group` changes to `vrf_attach_group`` under `vxlan.overlay_services.vrfs`
    - Network `attach_group` changes to `network_attach_group`` under `vxlan.overlay_services.networks`
* Support for Spanning-Tree in data model and fabric creation in NDFC 12.2.2 or later
* Support for IPv6 fabric underlay
* Support new and update pre-validation rules:
    - 201: Verify a spanning tree protocol mutually exclusive parameters
    - 202: Verify Fabric Underlay Supports Multicast for TRM
    - 203: Verify Fabric Underlay ISIS Authentication
    - 401: Cross Reference VRFs and Networks items in the Service Model
    - 402: Verify VRF elements are enabled in fabric overlay services
    - 403: Verify Network elements are enabled in fabric overlay services
    - 501: Verify Policy Cross Reference Between Policies, Groups, and Switches

Fixed
-----
- https://github.com/netascode/ansible-dc-vxlan/issues/21
- https://github.com/netascode/ansible-dc-vxlan/issues/67
- https://github.com/netascode/ansible-dc-vxlan/issues/104
- https://github.com/netascode/ansible-dc-vxlan/issues/119
- https://github.com/netascode/ansible-dc-vxlan/issues/120
- https://github.com/netascode/ansible-dc-vxlan/issues/151
- https://github.com/netascode/ansible-dc-vxlan/issues/153
- https://github.com/netascode/ansible-dc-vxlan/issues/170
- https://github.com/netascode/ansible-dc-vxlan/issues/184
- https://github.com/netascode/ansible-dc-vxlan/issues/188
- https://github.com/netascode/ansible-dc-vxlan/issues/192

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

.. _0.4.0: https://github.com/netascode/ansible-dc-vxlan/compare/0.3.0...0.4.0
.. _0.3.0: https://github.com/netascode/ansible-dc-vxlan/compare/0.2.0...0.3.0
.. _0.2.0: https://github.com/netascode/ansible-dc-vxlan/compare/0.1.0...0.2.0
.. _0.1.0: https://github.com/netascode/ansible-dc-vxlan/compare/0.1.0...0.1.0

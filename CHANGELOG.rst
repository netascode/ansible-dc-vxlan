=============================================================
Cisco Ansible NetworkAsCode DC VXLAN Collection Release Notes
=============================================================

All notable changes to this project will be documented in this file.

This project adheres to `Semantic Versioning <http://semver.org/>`_.

.. contents:: ``Release Versions``

`0.5.0`_
=====================

**Release Date:** ``2025-22-09``

Added
-----

* Added initial support for VXLAN eBGP EVPN fabric type that includes:
    * Fabric management
    * Underlay & Overlay configuration using provided documentation and examples: https://netascode.cisco.com/docs/data_models/vxlan/global/global/
    * Device discovery
    * vPC
    * Interfaces
    * Overlay (VRFs and Networks)
    * Policy
    * **Note**: eBGP EVPN fabric type introduces and only supports global configuration under `vxlan.global.ebgp`
* Added additional backwards compatiability support for NDFC 3.1
* Added support for creating and managing vPC domain / vPC pair in data model for external fabric
* Added support for L3VNI without VLAN for iBGP and eBGP EVPN fabric types
* Added support for additional LACP attributes in data model for port-channels
* Added support for individual per-switch credentials
    * Support documentation can be found here: https://github.com/netascode/ansible-dc-vxlan/blob/0.5.0/docs/SWITCH_CREDENTIALS_GUIDE.md
* Added support for breakout interfaces with pre-provision device workflows
* Added initial support for unified Nexus Dashboard 4.1 via legacy, backwards compatiable NDFC APIs

Modified
--------

* Updated iac-validate to use nac-validate in validate role
* Updated `vxlan.global` keys to align with supported fabric types
    * iBGP EVPN fabric type should use: `vxlan.global.ibgp`
    * External fabric type should use: `vxlan.global.external`
    * eBGP EVPN fabric type introduces properties `vxlan.global.ebgp` starting in this release, `0.5.0`
    * Backwards compatiability is provided for `vxlan.global` keys for iBGP and External fabric types
* Updated pointer to defaults used for ISN and MSD fabric types to use `defaults.vxlan.multisite` keys

Fixed
-----
* https://github.com/netascode/ansible-dc-vxlan/issues/301
* https://github.com/netascode/ansible-dc-vxlan/issues/315
* https://github.com/netascode/ansible-dc-vxlan/issues/337
* https://github.com/netascode/ansible-dc-vxlan/issues/383
* https://github.com/netascode/ansible-dc-vxlan/issues/390
* https://github.com/netascode/ansible-dc-vxlan/issues/407
* https://github.com/netascode/ansible-dc-vxlan/issues/413
* https://github.com/netascode/ansible-dc-vxlan/issues/425
* https://github.com/netascode/ansible-dc-vxlan/issues/430
* https://github.com/netascode/ansible-dc-vxlan/issues/435
* https://github.com/netascode/ansible-dc-vxlan/issues/439
* https://github.com/netascode/ansible-dc-vxlan/issues/441
* https://github.com/netascode/ansible-dc-vxlan/issues/442
* https://github.com/netascode/ansible-dc-vxlan/issues/443
* https://github.com/netascode/ansible-dc-vxlan/issues/445
* https://github.com/netascode/ansible-dc-vxlan/issues/447
* https://github.com/netascode/ansible-dc-vxlan/issues/451
* https://github.com/netascode/ansible-dc-vxlan/issues/457
* https://github.com/netascode/ansible-dc-vxlan/issues/458
* https://github.com/netascode/ansible-dc-vxlan/issues/466
* https://github.com/netascode/ansible-dc-vxlan/issues/468
* https://github.com/netascode/ansible-dc-vxlan/issues/472
* https://github.com/netascode/ansible-dc-vxlan/issues/490
* https://github.com/netascode/ansible-dc-vxlan/issues/505
* https://github.com/netascode/ansible-dc-vxlan/issues/513
* https://github.com/netascode/ansible-dc-vxlan/issues/528
* https://github.com/netascode/ansible-dc-vxlan/issues/532
* https://github.com/netascode/ansible-dc-vxlan/issues/537
* https://github.com/netascode/ansible-dc-vxlan/issues/540
* https://github.com/netascode/ansible-dc-vxlan/issues/545
* https://github.com/netascode/ansible-dc-vxlan/issues/550
* https://github.com/netascode/ansible-dc-vxlan/issues/551
* https://github.com/netascode/ansible-dc-vxlan/issues/553
* https://github.com/netascode/ansible-dc-vxlan/issues/555
* https://github.com/netascode/ansible-dc-vxlan/issues/558
* https://github.com/netascode/ansible-dc-vxlan/issues/566
* https://github.com/netascode/ansible-dc-vxlan/issues/589
* https://github.com/netascode/ansible-dc-vxlan/issues/595

`0.4.3`_
=====================

**Release Date:** ``2025-07-02``

Added
-----

* Added support for manual underlay IP address allocation
* Added support for manually allocating vPC domain IDs
* Added support for breakout interfaces
* Added support for dot1q interface type
* Added support for orphan ports, duplex, and native VLAN for interface types access, access port-channel, trunk, and trunk port-channel

Modified
--------

* Updated defaults to include ``domain_id`` and ``lb_id`` defaults for PTP
* Removed the requirement to have ports defined for ``vxlan.overlay.networks.network_attach_groups`` in VXLAN fabrics
* Updated POAP and pre-provision workflow
    * This update allows devices to be discovered using discovery mode, poap and pre-provision workflows. Previously the solution did not allow both poap and pre-provision in the same datafile.
    * Note: The poap.boostrap setting under the device is only used for POAP mode without pre-provision first. It is not used by a pre-provision or pre-provision + POAP workflow.

Fixed
-----
* https://github.com/netascode/ansible-dc-vxlan/issues/32
* https://github.com/netascode/ansible-dc-vxlan/issues/388
* https://github.com/netascode/ansible-dc-vxlan/issues/391
* https://github.com/netascode/ansible-dc-vxlan/issues/400
* https://github.com/netascode/ansible-dc-vxlan/issues/405
* https://github.com/netascode/ansible-dc-vxlan/issues/409
* https://github.com/netascode/ansible-dc-vxlan/issues/411
* https://github.com/netascode/ansible-dc-vxlan/issues/421
* https://github.com/netascode/ansible-dc-vxlan/issues/424

`0.4.2`_
=====================

**Release Date:** ``2025-06-02``

Added
-----

* Added support for the following model properties:
    - ``vxlan.multisite.layer2_vni_range``
    - ``vxlan.multisite.layer3_vni_range``
    - ``vxlan.global.layer2_vni_range``
    - ``vxlan.global.layer3_vni_range``
    - ``vxlan.global.layer2_vlan_range``
    - ``vxlan.global.layer3_vlan_range``
    - ``vxlan.underlay.ipv6.underlay_routing_loopback_ip_range``
    - ``vxlan.underlay.ipv6.underlay_vtep_loopback_ip_range``
    - ``vxlan.underlay.ipv6.underlay_rp_loopback_ip_range``
    - ``vxlan.underlay.ipv6.underlay_subnet_ip_range``
    - ``vxlan.underlay.multicast.ipv4.authentication_enable``
    - ``vxlan.underlay.multicast.ipv4.authentication_key``
    - ``vxlan.underlay.multicast.ipv6.group_subnet``
    - ``vxlan.underlay.multicast.ipv6.trmv6_enable``
    - ``vxlan.underlay.multicast.ipv6.trmv6_default_group``

Modified
--------

* The following keys have been relocated under ``vxlan.underlay.ipv4`` and data model files will need to be updated accordingly:
    - ``vxlan.underlay.ipv4.fabric_interface_numbering``
    - ``vxlan.underlay.ipv4.subnet_mask``
* The following keys have been relocated under ``vxlan.underlay.multicast.ipv4`` and data model files will need to be updated accordingly:
    - ``vxlan.underlay.multicast.ipv4.group_subnet``
    - ``vxlan.underlay.multicast.ipv4.trm_enable``
    - ``vxlan.underlay.multicast.ipv4.trm_default_group``

Fixed
-----
* https://github.com/netascode/ansible-dc-vxlan/issues/239
* https://github.com/netascode/ansible-dc-vxlan/issues/262
* https://github.com/netascode/ansible-dc-vxlan/issues/349
* https://github.com/netascode/ansible-dc-vxlan/issues/350
* https://github.com/netascode/ansible-dc-vxlan/issues/352
* https://github.com/netascode/ansible-dc-vxlan/issues/371
* https://github.com/netascode/ansible-dc-vxlan/issues/373
* https://github.com/netascode/ansible-dc-vxlan/issues/380
* https://github.com/netascode/ansible-dc-vxlan/issues/386

`0.4.1`_
=====================

**Release Date:** ``2025-04-24``

Added
-----

* Added ability to manage edge connections to external fabrics
* Added support for checking if a fabric is in a multisite domain and disallow management of ``vxlan.overlay.vrfs`` and ``vxlan.overlay.networks`` under the child fabric

Modified
--------

* Added various multisite fixes and introduced new ``child_fabrics`` model key under ``vxlan.multisite.overlay.vrfs`` and ``vxlan.multisite.overlay.networks`` for defining site-specific attributes

Fixed
-----

* https://github.com/netascode/ansible-dc-vxlan/issues/232
* https://github.com/netascode/ansible-dc-vxlan/issues/274
* https://github.com/netascode/ansible-dc-vxlan/issues/292
* https://github.com/netascode/ansible-dc-vxlan/issues/293
* https://github.com/netascode/ansible-dc-vxlan/issues/294
* https://github.com/netascode/ansible-dc-vxlan/issues/295
* https://github.com/netascode/ansible-dc-vxlan/issues/296
* https://github.com/netascode/ansible-dc-vxlan/issues/302
* https://github.com/netascode/ansible-dc-vxlan/issues/303
* https://github.com/netascode/ansible-dc-vxlan/issues/308
* https://github.com/netascode/ansible-dc-vxlan/issues/311
* https://github.com/netascode/ansible-dc-vxlan/issues/314
* https://github.com/netascode/ansible-dc-vxlan/issues/320
* https://github.com/netascode/ansible-dc-vxlan/issues/325
* https://github.com/netascode/ansible-dc-vxlan/issues/327
* https://github.com/netascode/ansible-dc-vxlan/issues/331
* https://github.com/netascode/ansible-dc-vxlan/issues/335
* https://github.com/netascode/ansible-dc-vxlan/issues/336
* https://github.com/netascode/ansible-dc-vxlan/issues/340
* https://github.com/netascode/ansible-dc-vxlan/issues/343
* https://github.com/netascode/ansible-dc-vxlan/issues/345
* https://github.com/netascode/ansible-dc-vxlan/issues/355

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
    * Only MSD is supported for MultiSite deployments.  MFD will be supported in a future release.
* NEW Feature: Support for managing inter-fabric links and External fabrics with ansible tag support to limit execution
* Enhanced data model validation and preprocessing
* Added new model keys for defining fabric ``name`` and ``type``

Example:

.. code-block:: yaml

    vxlan:
        fabric:
            name: nac-fabric1
            type: VXLAN_EVPN # Other allowed fabric types: MSD, ISN, External
        global:
            # name: nac-fabric1
            # fabric_type: VXLAN_EVPN


The ``name`` and ``fabric`` keys under ``vxlan.global`` are still supported but will be deprecated in future releases.

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

.. _0.5.0: https://github.com/netascode/ansible-dc-vxlan/compare/0.4.3...0.5.0
.. _0.4.3: https://github.com/netascode/ansible-dc-vxlan/compare/0.4.2...0.4.3
.. _0.4.2: https://github.com/netascode/ansible-dc-vxlan/compare/0.4.1...0.4.2
.. _0.4.1: https://github.com/netascode/ansible-dc-vxlan/compare/0.4.0...0.4.1
.. _0.4.0: https://github.com/netascode/ansible-dc-vxlan/compare/0.3.0...0.4.0
.. _0.3.0: https://github.com/netascode/ansible-dc-vxlan/compare/0.2.0...0.3.0
.. _0.2.0: https://github.com/netascode/ansible-dc-vxlan/compare/0.1.0...0.2.0
.. _0.1.0: https://github.com/netascode/ansible-dc-vxlan/compare/0.1.0...0.1.0

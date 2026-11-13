class Rule:
    id = "209"
    description = "Verify per-VRF per-VTEP loopback auto-provision mutual exclusivity"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []

        # Map controller fabric types to the data model keys (iBGP / eBGP only).
        fabric_type_map = {
            "VXLAN_EVPN": "ibgp",
            "eBGP_VXLAN": "ebgp",
        }
        fabric_type = fabric_type_map.get(cls.safeget(data_model, ['vxlan', 'fabric', 'type']))

        # These settings only exist on iBGP/eBGP VXLAN fabrics.
        if fabric_type is None:
            return results

        base = ['vxlan', 'global', fabric_type]

        # Pre-merge: only an explicit True counts as enabled. An omitted flag is
        # None here and resolves to the factory default (false) after merge_defaults.
        non_unique_enabled = (
            cls.safeget(data_model, base + ['vrf_vtep_loopback', 'ipv4', 'auto_provision']) is True or
            cls.safeget(data_model, base + ['vrf_vtep_loopback', 'ipv6', 'auto_provision']) is True
        )
        unique_enabled = (
            cls.safeget(data_model, base + ['vrf_vtep_unique_loopback', 'ipv4', 'auto_provision']) is True or
            cls.safeget(data_model, base + ['vrf_vtep_unique_loopback', 'ipv6', 'auto_provision']) is True
        )

        # Unique and non-unique per-VRF loopback are mutually exclusive: enabling
        # any unique auto-provision forbids any non-unique auto-provision.
        if unique_enabled and non_unique_enabled:
            prefix = f"vxlan.global.{fabric_type}"
            results.append(
                f"{prefix}: per-VRF per-VTEP unique and non-unique loopback auto-provision "
                f"are mutually exclusive. When any unique auto-provision "
                f"({prefix}.vrf_vtep_unique_loopback.ipv4.auto_provision / "
                f"{prefix}.vrf_vtep_unique_loopback.ipv6.auto_provision) is true, "
                f"the non-unique auto-provision flags "
                f"({prefix}.vrf_vtep_loopback.ipv4.auto_provision / "
                f"{prefix}.vrf_vtep_loopback.ipv6.auto_provision) must not be true."
            )

        return results

    @classmethod
    def safeget(cls, dict, keys):
        # Utility function to safely get nested dictionary values
        for key in keys:
            if dict is None:
                return None
            if key in dict:
                dict = dict[key]
            else:
                return None

        return dict

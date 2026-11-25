class Rule:
    id = "407"
    description = "Verify private VLAN network attributes"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        fabric_type = {"VXLAN_EVPN": "ibgp", "eBGP_VXLAN": "ebgp"}.get(
            cls.safeget(data_model, ['vxlan', 'fabric', 'type'])
        )
        overlay = cls.safeget(data_model, ['vxlan', 'overlay']) or cls.safeget(data_model, ['vxlan', 'overlay_services']) or {}
        networks = overlay.get('networks') or []
        pvlan_networks = [net for net in networks if net.get('pvlan_type') or net.get('pvlan_primary')]
        if not pvlan_networks:
            return results

        # Factory default is false, so a missing key pre-merge means disabled.
        if not cls.safeget(data_model, ['vxlan', 'global', fabric_type, 'enable_pvlan']):
            results.append(
                f"vxlan.global.{fabric_type}.enable_pvlan must be true when vxlan.overlay.networks use pvlan_type."
            )

        types = {net.get('name'): net.get('pvlan_type') for net in networks}
        isolated_per_primary = {}
        groups = {group.get('name'): group for group in overlay.get('network_attach_groups') or []}

        for net in pvlan_networks:
            name = net.get('name')
            prefix = f"vxlan.overlay.networks.{name}: "
            pvlan_type = net.get('pvlan_type')
            primary = net.get('pvlan_primary')

            if pvlan_type in ('isolated', 'community'):
                if primary is None:
                    results.append(prefix + f"pvlan_primary is required when pvlan_type is '{pvlan_type}'.")
                elif types.get(primary) != 'primary':
                    results.append(prefix + f"pvlan_primary '{primary}' must name a network with pvlan_type 'primary'.")
                if pvlan_type == 'isolated' and primary is not None:
                    isolated_per_primary.setdefault(primary, []).append(name)
                if not net.get('is_l2_only'):
                    results.append(prefix + f"is_l2_only must be true when pvlan_type is '{pvlan_type}'.")
                for key in ('vrf_name', 'gw_ip_address', 'gw_ipv6_address'):
                    if net.get(key) is not None:
                        results.append(prefix + f"{key} is not supported when pvlan_type is '{pvlan_type}'.")
            elif primary is not None:
                results.append(prefix + "pvlan_primary is only valid when pvlan_type is 'isolated' or 'community'.")

            group = groups.get(net.get('network_attach_group')) or {}
            if pvlan_type and any(switch.get('tors') for switch in group.get('switches') or []):
                results.append(
                    prefix + f"network_attach_group '{group.get('name')}' has tors, "
                    "which are not supported for private VLAN networks."
                )

        for primary, isolated in isolated_per_primary.items():
            if len(isolated) > 1:
                results.append(
                    f"vxlan.overlay.networks.{primary}: a primary network can have only one isolated network, "
                    f"found {', '.join(isolated)}."
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

import re


class Rule:
    id = "328"
    description = (
        "Verify vpc_peer_link QoS/STP settings are defined identically on both vPC peers "
        "and target the fabric peer-link port-channel"
    )
    severity = "HIGH"

    PL_KEYS = ("enable_qos", "qos_policy", "enable_qos_stats", "spanning_tree_port_type")

    @classmethod
    def match(cls, data_model):
        results = []
        vxlan = data_model.get("vxlan") or {}
        topology = vxlan.get("topology") or {}
        switches = {s.get("name"): s for s in topology.get("switches") or []}

        fabric_type = (vxlan.get("fabric") or {}).get("type")
        gkey = "ebgp" if fabric_type == "eBGP_VXLAN" else "ibgp"
        # Pre-merge: absent means the factory default (500).
        po_id = ((((vxlan.get("global") or {}).get(gkey) or {}).get("vpc") or {})
                 .get("peer_link_port_channel_id", 500))

        for pair in topology.get("vpc_peers") or []:
            names = (pair.get("peer1"), pair.get("peer2"))
            links = [cls.peer_link(switches.get(n)) for n in names]
            if not any(cls.keys_set(link) for link in links):
                continue
            where = f"vxlan.topology.vpc_peers[{names[0]}/{names[1]}]"
            if not all(links):
                results.append(f"{where}: peer-link QoS/STP settings require a vpc_peer_link interface on both peers")
                continue
            n1, n2 = (cls.norm(link.get("name")) for link in links)
            if n1 != n2:
                results.append(f"{where}: vpc_peer_link interface names differ ({links[0].get('name')} vs {links[1].get('name')})")
            if n1 != f"port-channel{po_id}":
                results.append(f"{where}: vpc_peer_link interface {links[0].get('name')} must be port-channel{po_id} "
                               "(the fabric peer-link port-channel)")
            for key in cls.PL_KEYS:
                if links[0].get(key) != links[1].get(key):
                    results.append(f"{where}: vpc_peer_link {key} must be the same on both peers "
                                   f"({links[0].get(key)!r} vs {links[1].get(key)!r})")
        return results

    @classmethod
    def peer_link(cls, switch):
        for interface in (switch or {}).get("interfaces") or []:
            if interface.get("mode") == "vpc_peer_link":
                return interface
        return None

    @classmethod
    def keys_set(cls, link):
        return bool(link) and any(k in link for k in cls.PL_KEYS)

    @staticmethod
    def norm(name):
        return re.sub(r"(?i)^(port-channel|po)", "port-channel", str(name or "")).lower()

import re


# Regex for validating strings
ANYCAST_GW_MAC = re.compile(
    r'^(?:'
    r'[a-f0-9]{2}-[a-f0-9]{2}-[a-f0-9]{2}-[a-f0-9]{2}-[a-f0-9]{2}-[a-f0-9]{2}'              # Hyphen format, e.g., 12-34-56-78-9a-bc
    r'|[a-f0-9]{2}:[a-f0-9]{2}:[a-f0-9]{2}:[a-f0-9]{2}:[a-f0-9]{2}:[a-f0-9]{2}'             # Colon format, e.g., 12:34:56:78:9a:bc
    r'|[a-f0-9]{4}\.[a-f0-9]{4}\.[a-f0-9]{4}'                                               # Cisco format, e.g., 1234.5678.9abc
    r'|[a-f0-9]\.[a-f0-9]\.[a-f0-9]'                                                        # Dot format with single hex digits, e.g., 1.2.3
    r')$',
    re.IGNORECASE
)


class Rule:
    id = "405"
    description = "Validate string values in the data model for VXLAN fabric to ensure they adhere to expected formats."
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []

        # Map fabric types to the keys used in the data model based on controller fabric types
        fabric_type_map = {
            "VXLAN_EVPN": "ibgp",
            "eBGP_VXLAN": "ebgp",
        }

        fabric_type = fabric_type_map.get(data_model['vxlan']['fabric']['type'])
        anycast_gw_mac = cls.safeget(data_model, ['vxlan', 'global', fabric_type, 'anycast_gateway_mac'])

        # Validate Anycast Gateway MAC address
        if anycast_gw_mac and not ANYCAST_GW_MAC.search(anycast_gw_mac):
            results.append(
                f"vxlan.global.{fabric_type}.anycast_gateway_mac is invalid. "
                "Only XX-XX-XX-XX-XX-XX, XX:XX:XX:XX:XX:XX, XXXX.XXXX.XXXX, X.X.X format are allowed (no case sensitive)"
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

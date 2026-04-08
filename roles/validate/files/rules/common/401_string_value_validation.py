import re


# Regex for validating names
FABRIC_NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{0,63}$')
VRF_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9.:_-]{0,32}$')                           # Length based on NX-OS limit, ND does not have a specific limit
NETWORK_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9.:_-]*$')
VLAN_NAME_PATTERN = re.compile(r'^[^?,\\\s]{0,128}$')


class Rule:
    id = "401"
    description = "Validate string values in the data model to ensure they adhere to expected formats."
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []

        if data_model.get("vxlan", None):

            # Validate Fabric name
            if data_model["vxlan"].get("fabric", None):
                fabric_name = data_model["vxlan"]["fabric"].get("name", None)

                if not FABRIC_NAME_PATTERN.search(fabric_name):
                    results.append(
                        f"vxlan.fabric.'{fabric_name}' is invalid. "
                        "Only a-z, A-Z, 0-9, _, - characters are allowed and name should start with an alphabet, "
                        "and max length must be 64 characters"
                    )

            if data_model["vxlan"].get("overlay", None):

                # Validate VRF keys
                if data_model["vxlan"]["overlay"].get("vrfs", None):
                    cls.check_vrfs_names(data_model["vxlan"]["overlay"]["vrfs"], results)

                # Validate Network keys
                if data_model["vxlan"]["overlay"].get("networks", None):
                    cls.check_networks_names(data_model["vxlan"]["overlay"]["networks"], results)

        return results

    @classmethod
    def check_vrfs_names(cls, vrfs, results):
        for vrf in vrfs:
            vrf_name = vrf.get("name", None)
            vrf_vlan_name = vrf.get("vrf_vlan_name", None)

            # Validate VRF name
            if not VRF_NAME_PATTERN.search(vrf_name):
                results.append(
                    f"vxlan.overlay.vrfs.{vrf_name} is invalid. "
                    "Only a-z, A-Z, 0-9, ., :, _, - characters are allowed and max length must be 32 characters"
                )
            # Validate VRF VLAN name
            if not VLAN_NAME_PATTERN.search(vrf_vlan_name):
                results.append(
                    f"vxlan.overlay.vrfs.{vrf_name}.vrf_vlan_name.'{vrf_vlan_name}' is invalid. "
                    "Name cannot contain spaces, ?, \\, ',' and max length must be 128 characters"
                )

    @classmethod
    def check_networks_names(cls, networks, results):
        for network in networks:
            network_name = network.get("name", None)
            vlan_name = network.get("vlan_name", None)

            # Validate Network name
            if not NETWORK_NAME_PATTERN.search(network_name):
                results.append(
                    f"vxlan.overlay.networks.{network_name} is invalid. "
                    "Only a-z, A-Z, 0-9, ., :, _, - characters are allowed"
                )

            # Validate VLAN name
            if vlan_name and not VLAN_NAME_PATTERN.search(vlan_name):
                results.append(
                    f"vxlan.overlay.networks.{network_name}.vlan_name.'{vlan_name}' is invalid. "
                    "Name cannot contain spaces, ?, \\, ',' and max length must be 128 characters"
                )

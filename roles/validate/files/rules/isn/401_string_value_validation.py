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

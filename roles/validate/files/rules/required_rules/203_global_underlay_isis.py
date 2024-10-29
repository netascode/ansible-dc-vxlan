class Rule:
    id = "203"
    description = "Verify Fabric Underlay ISIS Authentication"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []

        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("underlay", None):
                if inventory["vxlan"].get("underlay").get("isis", None):
                    if inventory["vxlan"].get("underlay").get("isis").get("authentication_enable"):
                        if inventory["vxlan"]["underlay"]["isis"]["authentication_enable"] is True:
                            if not inventory["vxlan"]["underlay"]["isis"].get("authentication_key"):
                                results.append(
                                    "For vxlan.underlay.isis.authentication_enable is enabled, "
                                    "vxlan.underlay.isis.authentication_key must be provided"
                                )
                            if not inventory["vxlan"]["underlay"]["isis"].get("authentication_keychain_name"):
                                results.append(
                                    "For vxlan.underlay.isis.authentication_enable is enabled, "
                                    "vxlan.underlay.isis.authentication_keychain_name must be provided"
                                )
        return results

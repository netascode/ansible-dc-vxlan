class Rule:
    id = "203"
    description = "Verify fabric underlay ISIS authentication"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []

        if data_model.get("vxlan", None):
            if data_model["vxlan"].get("underlay", None):
                if data_model["vxlan"].get("underlay").get("isis", None):
                    if data_model["vxlan"].get("underlay").get("isis").get("authentication_enable"):
                        if data_model["vxlan"]["underlay"]["isis"]["authentication_enable"] is True:
                            if not data_model["vxlan"]["underlay"]["isis"].get("authentication_key"):
                                results.append(
                                    "For vxlan.underlay.isis.authentication_enable is enabled, "
                                    "vxlan.underlay.isis.authentication_key must be provided"
                                )
                            if not data_model["vxlan"]["underlay"]["isis"].get("authentication_keychain_name"):
                                results.append(
                                    "For vxlan.underlay.isis.authentication_enable is enabled, "
                                    "vxlan.underlay.isis.authentication_keychain_name must be provided"
                                )
        return results

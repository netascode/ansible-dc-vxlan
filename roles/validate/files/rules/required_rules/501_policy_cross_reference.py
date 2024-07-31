class Rule:
    id = "501"
    description = "Verify Policy Cross Reference Between Policies, Groups, and Switches"
    severity = "HIGH"

    @classmethod
    def match(cls, inventory):
        results = []

        if inventory.get("vxlan", None):
            if inventory["vxlan"].get("policy", None):
                if inventory["vxlan"].get("policy").get("policies", None):
                    policies = inventory["vxlan"]["policy"]["policies"]
                if inventory["vxlan"].get("policy").get("groups", None):
                    groups = inventory["vxlan"]["policy"]["groups"]
                if inventory["vxlan"].get("policy").get("switches", None):
                    switches = inventory["vxlan"]["policy"]["switches"]

        return results


import os
class Rule:
    id = "501"
    description = "Verify policy cross reference between policies, groups, and switches"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        policies = []
        groups = []
        topology_switches = []
        results = []

        if data_model.get("vxlan", None):
            if data_model["vxlan"].get("policy", None):
                if data_model["vxlan"].get("policy").get("policies", None):
                    policies = data_model["vxlan"]["policy"]["policies"]
                    for policy in policies:
                        filename = policy.get("filename", None)

                        # Test if filename exists
                        if filename:
                            if not os.path.exists(os.path.expanduser(filename)):
                                results.append(
                                    f"Filename {filename} does not exist in policy: {policy.get('name')} "
                                )
                                break

                        if ((filename and policy.get("template_name", None) and policy.get("template_vars", None)) or
                                (filename and policy.get("template_vars", None))):
                            results.append(
                                "Policy definition filenames with .config or .cfg default template_name to NDFC freeform whereas "
                                "filenames with .yaml or .yml requires template_name to be defined per NDFC standards and "
                                "template_name and template_vars must not be defined together per NDFC standards."
                            )
                            break

                        if (filename and filename.endswith(('.config', '.cfg', '.yaml', '.yml'))) and policy.get("template_vars", None):
                            results.append(
                                f"Policy filename {filename} is of .config, .cfg, .yaml, or .yml extension. The template_vars parameter must not be defined."
                            )
                            break

                        if (filename and filename.endswith(('.yaml', '.yml'))) and not policy.get("template_name", None):
                            results.append(
                                f"Policy filename {filename} is of .yaml, or .yml extension. The template_name parameter must be defined."
                            )
                            break

                if data_model["vxlan"].get("policy").get("groups", None):
                    groups = data_model["vxlan"]["policy"]["groups"]
                    for group in groups:
                        group_policies = group.get("policies", [])
                        for group_policy in group_policies:
                            if not any(policy['name'] == group_policy['name'] for policy in policies):
                                results.append(
                                    f"Policy name {group_policy['name']} is defined in a group and must be defined in the policies section."
                                )
                                break

                if data_model["vxlan"].get("policy").get("switches", None):
                    switches = data_model["vxlan"]["policy"]["switches"]

                    if data_model.get("vxlan"):
                        if data_model["vxlan"].get("topology"):
                            if data_model.get("vxlan").get("topology").get("switches"):
                                topology_switches = data_model.get("vxlan").get("topology").get("switches")
                    for switch in switches:
                        if not ((any(topology_switch['name'] == switch['name'] for topology_switch in topology_switches)) or
                                (any(topology_switch['management'].get('management_ipv4_address', None) == switch['name']
                                     for topology_switch in topology_switches)) or
                                (any(topology_switch['management'].get('management_ipv6_address', None) == switch['name']
                                     for topology_switch in topology_switches))):
                            results.append(
                                f"Switch name {switch['name']} is defined and must be defined in the topology switches section."
                            )
                            break

                        switch_groups = switch.get("groups", [])
                        for switch_group in switch_groups:
                            for group in groups:
                                if not (any(group['name'] == switch_group for group in groups)):
                                    results.append(
                                        f"Policy group name {switch_group} is defined for switch {switch['name']} and "
                                        "must be defined in the policy groups section."
                                    )
                                    break

        return results

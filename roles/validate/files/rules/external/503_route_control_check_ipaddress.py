"""Rule 503 to check IP format"""
import ipaddress
import re


class Rule:
    """
    Class 503 - Verify IP address format for route control
    """

    id = "503"
    description = "Verify IP address format for route control"
    severity = "HIGH"
    results = []

    @classmethod
    def match(cls, data_model):
        """
        Matches and validates IP prefixes in the data_model based on provided keys and their entries.
        """
        cls.validate_prefix_lists(data_model, "ipv4_prefix_lists", "IPv4")
        cls.validate_prefix_lists(data_model, "ipv6_prefix_lists", "IPv6")
        cls.validate_acls(data_model, "ipv4_access_lists", "IPv4")
        cls.validate_acls(data_model, "ipv6_access_lists", "IPv6")

        return cls.results

    @classmethod
    def validate_acls(cls, data, acls_key, address_family):
        """
        Validates ACL entries for both 'source' and 'destination' host fields.

        :param data: The input data dictionary.
        :param acls_key: The key for the ACLs (e.g., 'ipv4_acls' or 'ipv6_acls').
        :param address_family: The address family label (e.g., 'IPv4' or 'IPv6').
        """
        acls = cls.safeget(data, ["vxlan", "overlay_extensions", "route_control", acls_key])
        if acls:
            for acl in acls:
                if "entries" in acl:
                    for entry in acl["entries"]:
                        # Validate the 'source' field
                        cls.validate_host_field(acl["name"], entry, "source", address_family)
                        # Validate the 'destination' field
                        cls.validate_host_field(acl["name"], entry, "destination", address_family)

    @classmethod
    def validate_host_field(cls, acl_name, entry, field, address_family):
        """
        Validates the 'host' or 'ip' field in the given ACL entry for either
        'source' or 'destination'.

        :param acl_name: The name of the ACL being validated.
        :param entry: The ACL entry dictionary.
        :param field: The field to validate ('source' or 'destination').
        :param address_family: The address family label (e.g., 'IPv4' or 'IPv6').
        """
        if field not in entry:
            return  # Skip validation if the field is not present in the entry

        # Validate the 'host' field
        cls._validate_host_field(acl_name, entry, field, address_family)

        # Validate the 'ip' field and handle wildcard configuration
        cls._validate_ip_field(acl_name, entry, field, address_family)

    @classmethod
    def _validate_host_field(cls, acl_name, entry, field, address_family):
        """
        Validates the 'host' field in the ACL entry.
        """
        host = entry[field].get("host")
        if host:
            # Valid IPv4 or IPv6 host regex
            host_regex = r"^(?:\d{1,3}\.){3}\d{1,3}$|^[\da-fA-F:]+$"

            # Check if the host matches the expected regex
            if not re.match(host_regex, host):
                message = f"Invalid format. '{host}' must not include a CIDR prefix."
                cls.results.append(f"In {address_family} ACL: {acl_name} {message}")

    @classmethod
    def _validate_ip_field(cls, acl_name, entry, field, address_family):
        """
        Validates the 'ip' field in the ACL entry and handles wildcard configuration.
        """
        ip = entry[field].get("ip")
        wildcard = entry[field].get("wildcard")

        if ip and wildcard:
            # Valid IPv4 or IPv6 host regex
            ip_regex = r"^(?:\d{1,3}\.){3}\d{1,3}$|^[\da-fA-F:]+$"

            # Check if the IP matches the expected regex
            if not re.match(ip_regex, ip):
                message = f"""Invalid format. '{ip
                }' must not include a CIDR prefix when wildcard is configured."""
                cls.results.append(f"In {address_family} ACL: {acl_name} {message}")

        elif ip:
            # Validate the IP as a CIDR if no wildcard is provided
            is_valid, message = cls.is_ip_cidr(ip)
            if not is_valid:
                cls.results.append(f"""In {address_family} ACL: {acl_name} {message
                } or use wildcard.""")

    @classmethod
    def validate_prefix_lists(cls, data, prefix_list_key, address_family):
        """
        Validates IPv4 or IPv6 prefix lists in the given data.

        :param data: The input data dictionary.
        :param prefix_list_key: The key for the prefix list
            (e.g., "ipv4_prefix_lists" or "ipv6_prefix_lists").
        :param address_family: The address family label (e.g., "IPv4" or "IPv6").
        """
        prefix_lists = cls.safeget(data, [
            "vxlan", "overlay_extensions", "route_control", prefix_list_key])
        if prefix_lists:
            for prefix in prefix_lists:
                if "entries" in prefix:
                    for entry in prefix["entries"]:
                        if "prefix" in entry:
                            is_valid, message = cls.is_ip_cidr(entry["prefix"])
                            if not is_valid:
                                cls.results.append(f"""In {address_family
                                } Prefix-List: {prefix['name']} {message}""")

    @classmethod
    def is_ip_cidr(cls, ip_cidr):
        """
        Validates if the input string is a valid CIDR notation (IPv4/IPv6).
        """
        # Regular expression for validating CIDR notation
        cidr_regex = r"^(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}$|^[\da-fA-F:]+/\d{1,3}$"

        # Check if the input matches the CIDR regex pattern
        if not re.match(cidr_regex, ip_cidr):
            return False, f"""Invalid format. '{ip_cidr
            }' must include a CIDR prefix (e.g., /24 for IPv4 or /64 for IPv6)"""

        try:
            # Check if it can be parsed as a valid IPv4 or IPv6 network
            ipaddress.ip_network(ip_cidr, strict=True)
            return True, f"'{ip_cidr}' is a valid IP address with CIDR prefix."
        except ValueError as e:
            return False, f"Invalid IP or CIDR: {e}"

    @classmethod
    def data_model_key_check(cls, tested_object, keys):
        """
        Checks for the presence of specific keys in the nested data model and categorizes them.
        """
        dm_key_dict = {'keys_found': [], 'keys_not_found': [], 'keys_data': [], 'keys_no_data': []}
        for key in keys:
            if tested_object and key in tested_object:
                dm_key_dict['keys_found'].append(key)
                tested_object = tested_object[key]
                if tested_object:
                    dm_key_dict['keys_data'].append(key)
                else:
                    dm_key_dict['keys_no_data'].append(key)
            else:
                dm_key_dict['keys_not_found'].append(key)
        return dm_key_dict

    @classmethod
    def safeget(cls, dictionary, keys):
        """
        Safely retrieves nested values from a dictionary using a list of keys.
        """
        for key in keys:
            if dictionary is None or key not in dictionary:
                return None
            dictionary = dictionary[key]
        return dictionary

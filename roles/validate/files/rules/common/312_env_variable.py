class Rule:
    id = "312"
    description = "Verify NDFC_SW_DISCOVERY_PASSWORD environment variable minimum length"
    severity = "HIGH"

    @classmethod
    def match(cls, data_model):
        results = []
        import os
        # Check if NDFC_SW_DISCOVERY_PASSWORD environment variable is declared
        env_var_name = 'NDFC_SW_DISCOVERY_PASSWORD'

        # Use get() to safely retrieve the variable (returns None if not declared)
        password = os.environ.get(env_var_name)

        # Handle case where variable is not declared or is empty
        if password is None:
            results.append(
                f"Environment variable '{env_var_name}' is not declared. "
                "This variable is required for switch discovery operations."
            )
            return results

        if password == '':
            results.append(
                f"Environment variable '{env_var_name}' is declared but empty. "
                "A non-empty password is required."
            )
            return results

        # Check minimum password length (8 characters)
        min_length = 8
        if len(password) < min_length:
            results.append(
                f"Environment variable '{env_var_name}' has length of {len(password)} characters. "
                f"Minimum required length is {min_length} characters."
            )
            return results

        return results

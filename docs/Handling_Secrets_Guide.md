# Handling Secrets Guide

This guide describes how to manage secrets such as passwords and authentication keys in the Network as Code VXLAN data model. There are two mechanisms available:

1. **Ansible Vault** - Encrypts entire variable values at rest.
2. **Environment Variable Lookup (`env_var_`)** - Resolves secrets from environment variables at runtime. Suitable for CI/CD integration.

Both approaches ensure that plaintext secrets are not visible in the data YAML files. The key difference is that Ansible Vault encrypts whole values while `env_var_` replaces individual strings — making `env_var_` the only option for secrets embedded in freeform configuration blocks.

---

## Ansible Vault

[Ansible Vault](https://docs.ansible.com/ansible/latest/vault_guide/index.html) encrypts sensitive data so it can be stored safely in data files. Encrypted values are decrypted automatically at playbook runtime when a vault password is provided.

### Encrypting a Value

```bash
ansible-vault encrypt_string 'MySecretPassword' --name 'authentication_key'
```

This produces an encrypted variable which you can paste into your data files:

```yaml
vxlan:
  underlay:
    bgp:
      authentication_enable: true
      authentication_key_type: 3
      authentication_key: !vault |
        $ANSIBLE_VAULT;1.1;AES256
        61626364656667686970...
```

### Running Playbooks with Vault

```bash
# Prompt for vault password
ansible-playbook -i inventory deploy.yaml --ask-vault-pass

# Use a password file
ansible-playbook -i inventory deploy.yaml --vault-password-file ~/.vault_pass
```

### Limitation: Freeform Configurations

Ansible Vault encrypts the entire value of a YAML field. This works for standalone fields like `authentication_key` where the complete value is a secret.

However, freeform configuration blocks may contain a mix of regular configuration and secrets within a single multi-line string:

```yaml
# Does not work with Ansible Vault because only the TACACS key is a secret,
# not the entire block.
aaa_freeform: |
  feature tacacs+
  tacacs-server key 7 MySecretTacacsKey
  ip tacacs source-interface mgmt0
  tacacs-server timeout 20
```

Encrypting the entire `aaa_freeform` value with Ansible Vault would encrypt all four lines, which is not desired.

---

## Environment Variable Lookup (`env_var_`)

The `env_var_` prefix instructs NaC to resolve a value from an environment variable at runtime. This works for:

- **Standalone values** - the entire YAML value is an reference to an environment variable
- **Embedded secrets** - `env_var_` references inside larger strings (e.g. freeform configuration blocks)

### How It Works

Any string value in the data model that contains `env_var_` is resolved by the NaC VXLAN `validate` role. The secret is replaced with the value of the corresponding environment variable.

* Variable names in YAML must exactly match the environment variable names (including the env_var_ prefix).
* Valid environment variable names may include letters, digits, and underscores.
* Use single quotes to prevent shell interpretation of special characters
* If the environment variable is not set, a warning is displayed and the secret is left unchanged.

### Setting Environment Variables

```bash
export env_var_BGP_AUTH_KEY='MyBgpP@$$w0rd'
export env_var_MCAST_AUTH_KEY='mcast_secret_123'
export env_var_TACACS_KEY='TacacsSecret!'
export env_var_DCI_PASSWORD='DciP@ssword'
```

### Examples: Standalone Values

```yaml
vxlan:
  underlay:
    multicast:
      ipv4:
        authentication_enable: true
        authentication_key: env_var_MCAST_AUTH_KEY
    bgp:
      authentication_enable: true
      authentication_key_type: 3
      authentication_key: env_var_BGP_AUTH_KEY
```

```yaml
vxlan:
  multisite:
    overlay_dci:
      enable_ebgp_password: True
      ebgp_password: env_var_DCI_PASSWORD
      ebgp_password_encryption_type: 3
```

### Example: Freeform Configurations

```yaml
vxlan:
  global:
    ebgp:
      aaa_freeform: |
        feature tacacs+
        tacacs-server key 7 env_var_TACACS_KEY
        ip tacacs source-interface mgmt0
        tacacs-server timeout 20
```

At runtime, only `env_var_TACACS_KEY` is replaced with the value of the `env_var_TACACS_KEY` environment variable. The rest of the block is unchanged:

```
feature tacacs+
tacacs-server key 7 TacacsSecret!
ip tacacs source-interface mgmt0
tacacs-server timeout 20
```

This pattern works in any freeform field (`aaa_freeform`, `banner_freeform`, `bootstrap_freeform`, `intra_fabric_link_freeform`, `freeform_config`, etc.) and supports multiple `env_var_` tokens in the same block.

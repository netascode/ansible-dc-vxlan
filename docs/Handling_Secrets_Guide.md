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

Any string value in the data model that contains `env_var_` is resolved by NaC VXLAN. The string is replaced with the value of the corresponding environment variable.

* Resolution is global. Any string in the data model that contains `env_var_` followed by word characters (`env_var_\w+`) is treated as a token, not only known secret fields. This allows `env_var_` to work inside freeform blocks, but it also means ordinary text that happens to contain the prefix is rewritten.
* Variable names in YAML must exactly match the environment variable names (including the env_var_ prefix).
* Valid environment variable names may include letters, digits, and underscores.
* If a referenced environment variable is not set, the run fails during the `validate` stage. The error lists every missing variable with its location in the data model. This behavior prevents an unresolved `env_var_` string from being sent to Nexus Dashboard as a literal credential value.
* `env_var_` performs substitution only, it does not encrypt. The resolved value is passed to Nexus Dashboard exactly as stored in the environment variable, with no transformation. It is the operator's responsibility to store a value that already matches what the target field expects.
* For fields that carry an encryption type (for example `authentication_key` with `authentication_key_type: 3`, `ebgp_password` with `ebgp_password_encryption_type: 3`, or a `tacacs-server key 7 ...` line in a freeform block), the environment variable must contain the value already encoded for that type (the ciphertext), not the plaintext secret.
* To keep literal `env_var_...` text (for example in a banner) from being resolved, avoid the exact `env_var_` prefix. For example break the word so it does not match, or reword the text. There is no dedicated escape sequence.

### Setting Environment Variables

The value stored in each variable must already be encoded for the field that references it. The placeholders below stand for the encrypted (ciphertext) values, not plaintext secrets:

```bash
export env_var_BGP_AUTH_KEY='<3DES-encrypted BGP authentication key>'
export env_var_MCAST_AUTH_KEY='<3DES-encrypted PIM hello key>'
export env_var_TACACS_KEY='<type-7 encoded TACACS key>'
export env_var_DCI_PASSWORD='<3DES-encrypted DCI password>'
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

At runtime, only `env_var_TACACS_KEY` is replaced with the value of the `env_var_TACACS_KEY` environment variable. Because the line uses `key 7`, the variable must contain the type-7 encoded key (not the plaintext). The rest of the block is unchanged:

```
feature tacacs+
tacacs-server key 7 076a0f1e1d0a19173e243f36
ip tacacs source-interface mgmt0
tacacs-server timeout 20
```

This pattern works in any freeform field (`aaa_freeform`, `banner_freeform`, `bootstrap_freeform`, `intra_fabric_link_freeform`, `freeform_config`, etc.) and supports multiple `env_var_` tokens in the same block.

### Limitations

* The `env_var_` lookup mechanism is not supported for policies referencing a file.

* If an environment variable changes, the change will not be detected in case of a diff run (enabled by default), because the configuration in the data YAML files still looks the same. To enforce a new lookup, you can set the `force_run_all` parameter to true.

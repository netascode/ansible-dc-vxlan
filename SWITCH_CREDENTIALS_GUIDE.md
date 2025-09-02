# Using custom switch credentials in `topology_switches.nac.yaml`


## Quick checklist
- Define defaults in group_vars: `ndfc_switch_username`, `ndfc_switch_password`.
- For a specific switch, choose one:
  - Plain text (testing only), or
  - Environment variables using the exact `env_var_*` name, or  - Ansible Vault `!vault` values.
- If using Vault, configure a vault password file that Ansible can find.
- Run your playbook.

## How credentials are resolved
From `get_credentials.py`:
- Defaults must exist in group_vars: `ndfc_switch_username` and `ndfc_switch_password`.
- For each switch (matched by `management.management_ipv4_address`):
  - If both `management.username` and `management.password` are present, they’re used.
    - If a value starts with `env_var_`, its value is loaded from the environment.
    - If a value is `!vault`, nac_yaml decrypts it via `ansible-vault`.
  - Otherwise, defaults from group_vars are used.

---

## 1) Set defaults in group_vars (required)
Add to your appropriate group vars.



## 2) Option A — Plain text in the model (testing only)
```yaml
management:
  management_ipv4_address: 198.18.133.23
  username: admin
  password: "C1sco!23456"
```
Note: Not secure. Prefer environment variables or Vault.

---

## 3) Option B — Environment variables per switch
Set env variable names literally in the model (including the `env_var_` prefix):

```yaml
management:
  management_ipv4_address: 198.18.133.21
  username: env_var_spine21_username
  password: env_var_spine21_password
```
Export those variables in your shell before running Ansible (quote special chars):

```bash
export env_var_spine21_username='admin'
export env_var_spine21_password='S3cureP@ss!'
```
If a variable isn’t set, the code falls back to group_vars for that device.

---

## 4) Option C — Ansible Vault inline values

### 4.1 Create a vault password file
```bash
echo "your_vault_password_here" > /absolute/path/to/vault_password_file
chmod 600 /absolute/path/to/vault_password_file
```
`chmod 600` sets file permissions to read and write for the owner only, and no permissions for group or others. 
**Never commit this file.**

### 4.2 Make the password discoverable by Ansible
Pick one of the following:

- `ansible.cfg`:
```ini
[defaults]
vault_password_file = /absolute/path/to/vault_password_file
# or
vault_identity_list = default@/absolute/path/to/vault_password_file
```

- Environment variable:
```bash
export ANSIBLE_VAULT_PASSWORD_FILE=/absolute/path/to/vault_password_file
```

This is required so nac_yaml’s loader (which calls `ansible-vault` in a subprocess) can decrypt `!vault` values.

### 4.3 Encrypt the username and password
You can encrypt inline strings and paste the output blocks into the model:

```bash
echo -n 'admin' | ansible-vault encrypt_string --stdin-name 'username' --encrypt-vault-id default

echo -n 'S3cureP@ss!' | ansible-vault encrypt_string --stdin-name 'password' --encrypt-vault-id default
```

Paste results into the YAML (keep indentation consistent):

```yaml
management:
  management_ipv4_address: 198.18.133.11
  username: !vault |
    $ANSIBLE_VAULT;1.1;AES256
    <encrypted-block-for-username>
  password: !vault |
    $ANSIBLE_VAULT;1.1;AES256
    <encrypted-block-for-password>
```

VS Code may warn about `!vault`; it’s valid for Ansible.

---

## 5) Mixed example (reflecting a common setup)
```yaml
# SPINE_21 via environment variables
management:
  management_ipv4_address: 198.18.133.21
  username: env_var_spine21_username
  password: env_var_spine21_password

# SPINE_11 via Vault (ciphertext redacted)
management:
  management_ipv4_address: 198.18.133.11
  username: !vault |
    $ANSIBLE_VAULT;1.1;AES256
    ...
  password: !vault |
    $ANSIBLE_VAULT;1.1;AES256
    ...

# LEAF23 plain text (testing only)
management:
  management_ipv4_address: 198.18.133.23
  username: admin
  password: "C1sco!23456"

# LEAF24 uses group_vars defaults (no per-switch fields)
management:
  management_ipv4_address: 198.18.133.24
```

---

## 6) Run the playbook
If not configured in `ansible.cfg`, pass the vault password file on the command line:

```bash
ansible-playbook -i inventory.yaml \
  --vault-password-file /absolute/path/to/vault_password_file \
  vxlan_skaszlik-nac-fabric1.yaml
```

---

## FAQ: Can I decrypt with just a password (no vault_password_file)?
Short answer: no, not interactively. The nac_yaml loader invokes `ansible-vault` in a non-interactive subprocess via a `--vault-id` helper script, so it cannot prompt for a password. You must provide the secret non-interactively via one of:
- `vault_password_file` or `vault_identity_list` in `ansible.cfg`.
- An environment-based identity (e.g., a command in `vault_identity_list` that echoes a password).
- An env var consumed by the helper script used as `--vault-id` (inspect the helper at your site-packages path to see what it expects).

## Troubleshooting
- Decryption failed: “no vault secrets were found …”
  - Ensure `vault_password_file` or `vault_identity_list` is set in `ansible.cfg`, or `ANSIBLE_VAULT_PASSWORD_FILE` exported.
  - The vault file must contain the correct (non-empty) password and match the ciphertext.
- Environment variables not picked up:
  - Names must exactly match the YAML values (including `env_var_`).
  - Quote special characters in your shell: `export env_var_PASSWORD='S3cure$Th!ng'`.

## Security notes
- Don’t commit `vault_password_file`; add it to `.gitignore`.
- Prefer Vault or environment variables over plain text.
- Restrict permissions on the vault password file (`chmod 600`).



# Using custom switch credentials in `topology_switches.nac.yaml`

## Overview
This guide shows you how to configure switch credentials for NaC VXLAN deployments. You have three credential options available, each with different security levels and use cases.

## Quick Start: Choose Your Credential Method

### Option 1: Plain Text (Testing Only) ⚠️
```yaml
# topology_switches.nac.yaml
switches:
  - name: leaf-1
    management:
      management_ipv4_address: 198.18.133.3
      username: admin
      password: "C1sco!23456"
```
**Use Case**: Lab testing only
**Security**: ❌ Not secure - credentials visible in files

### Option 2: Environment Variables (Recommended for CI/CD) ✅
```yaml
# topology_switches.nac.yaml
switches:
  - name: leaf-2
    management:
      management_ipv4_address: 198.18.133.2
      username: env_var_leaf2_username
      password: env_var_leaf2_password
```
```bash
# Set these environment variables before running Ansible
export env_var_leaf2_username='admin'
export env_var_leaf2_password='S3cureP@ss!'
```
**Use Case**: CI/CD pipelines, automated deployments
**Security**: ✅ Secure - credentials not stored in files

### Option 3: Ansible Vault (Recommended for Production) 🔐
```yaml
# topology_switches.nac.yaml
switches:
  - name: leaf-3
    management:
      management_ipv4_address: 198.18.133.3
      username: !vault |
        $ANSIBLE_VAULT;1.1;AES256
        66386439653236336464643...
      password: !vault |
        $ANSIBLE_VAULT;1.1;AES256
        39663933363834613965383...
```
**Use Case**: Production deployments, long-term storage
**Security**: ✅ Highly secure - encrypted credentials

---

## Prerequisites: Set Default Credentials (Required)

Before using any credential method, you **must** define default credentials in your group variables. These serve as fallback values for switches without specific credentials.

### Basic Group Variables Setup

**Add to `group_vars/ndfc/main.yaml` or appropriate group vars file:**
```yaml
ndfc_switch_username: admin
ndfc_switch_password: default_password
```

### Advanced Group Variables with Environment Lookups

For enhanced security, you can use environment variable lookups in your group_vars files:

**Example 1: Direct environment lookups for NDFC credentials**
```yaml
# group_vars/ndfc/main.yaml
# Credentials for switches in inventory
ndfc_switch_username: "{{ lookup('env', 'NDFC_SW_USERNAME') }}"
ndfc_switch_password: "{{ lookup('env', 'NDFC_SW_PASSWORD') }}"
```

**Example 2: Environment lookups with fallback defaults**
```yaml
# group_vars/ndfc/main.yaml
# Primary credentials with fallbacks
ndfc_switch_username: "{{ lookup('env', 'NDFC_SW_USERNAME') | default('admin') }}"
ndfc_switch_password: "{{ lookup('env', 'NDFC_SW_PASSWORD') | default('default_password') }}"
```

**Setting the corresponding environment variables:**
```bash
# Set environment variables for group_vars lookups
export NDFC_SW_USERNAME='admin'
export NDFC_SW_PASSWORD='secure_default_password'
export env_var_leaf_username='leaf_admin'
export env_var_leaf_password='leaf_secure_password'
```

## How Credential Resolution Works

The system resolves credentials using this priority order:

1. **Switch-specific credentials** (if both `username` and `password` are defined in switch management)
   - Environment variables (values starting with `env_var_`)
   - Vault encrypted values (values starting with `!vault`)
   - Plain text values
2. **Group default credentials** (fallback if no switch-specific credentials found)

**Credential matching**: Switches are matched by their `management.management_ipv4_address` field.


---

## Detailed Implementation Guide

### Step 1: Configure Default Credentials (Required First Step)

**Location**: `group_vars/ndfc/main.yaml` or appropriate group vars file

**Basic configuration:**
```yaml
ndfc_switch_username: admin
ndfc_switch_password: default_password
```

**Advanced configuration with environment lookups:**
```yaml
# Credentials for switches in inventory
ndfc_switch_username: "{{ lookup('env', 'NDFC_SW_USERNAME') }}"
ndfc_switch_password: "{{ lookup('env', 'NDFC_SW_PASSWORD') }}"
```

**Required environment variables for advanced configuration:**
```bash
# Set these environment variables before running Ansible
export NDFC_SW_USERNAME='admin'
export NDFC_SW_PASSWORD='secure_default_password'
export env_var_leaf_username='leaf_admin'
export env_var_leaf_password='leaf_secure_password'
```

⚠️ **Important**: These defaults are required and serve as fallback credentials for any switch that doesn't have specific credentials defined.

### Step 2: Choose and Implement Your Credential Method

#### Method A: Plain Text Credentials (Testing Only)

**When to use**: Lab environments, proof-of-concept testing
**Security level**: ❌ **INSECURE** - credentials visible in plain text

**Implementation**:
```yaml
# topology_switches.nac.yaml
switches:
  - name: leaf-4
    management:
      management_ipv4_address: 198.18.133.4
      username: admin
      password: "C1sco!23456"
```

**Pros**: Simple, no additional setup required
**Cons**: Credentials stored in plain text, not suitable for production

---

#### Method B: Environment Variables (Recommended for CI/CD)

**When to use**: CI/CD pipelines, automated deployments, development environments
**Security level**: ✅ **SECURE** - credentials not stored in files

**Implementation**:

**Step 1**: Configure switch with environment variable names
```yaml
# topology_switches.nac.yaml
switches:
  - name: leaf-5
    management:
      management_ipv4_address: 198.18.133.5
      username: env_var_leaf5_username
      password: env_var_leaf5_password
```

**Step 2**: Set environment variables before running Ansible
```bash
# Set these environment variables (quote special characters)
export env_var_leaf5_username='admin'
export env_var_leaf5_password='S3cureP@ss!'

# Verify they're set
echo $env_var_leaf5_username
echo $env_var_leaf5_password
```

**Important Notes**:
- Variable names in YAML must exactly match environment variable names (including `env_var_` prefix)
- Always quote passwords with special characters in your shell
- If environment variable is not set, system falls back to group_vars defaults
- Environment variables are session-specific and don't persist across terminal sessions

**Pros**: Secure, good for automation, easy to rotate credentials
**Cons**: Requires environment setup, credentials don't persist across sessions

---

#### Method C: Ansible Vault (Recommended for Production)

**When to use**: Production deployments, long-term credential storage
**Security level**: 🔐 **HIGHLY SECURE** - encrypted credentials

**Implementation**:

**Step 1**: Create a vault password file
```bash
# Create the vault password file
echo "your_vault_password_here" > /absolute/path/to/vault_password_file

# Secure the file (read/write for owner only)
chmod 600 /absolute/path/to/vault_password_file
```

⚠️ **Security**: Never commit this file to version control. Add it to `.gitignore`.

**Step 2**: Configure Ansible to find the vault password

Choose one of these methods:

**Option A - ansible.cfg** (Recommended):
```ini
[defaults]
vault_password_file = /absolute/path/to/vault_password_file
# or
vault_identity_list = default@/absolute/path/to/vault_password_file
```

**Option B - Environment variable**:
```bash
export ANSIBLE_VAULT_PASSWORD_FILE=/absolute/path/to/vault_password_file
```

**Step 3**: Encrypt credentials
```bash
# Encrypt username
echo -n 'admin' | ansible-vault encrypt_string --stdin-name 'username' --encrypt-vault-id default

# Encrypt password
echo -n 'S3cureP@ss!' | ansible-vault encrypt_string --stdin-name 'password' --encrypt-vault-id default
```

**Step 4**: Add encrypted values to YAML
```yaml
# topology_switches.nac.yaml
switches:
  - name: leaf-6
    management:
      management_ipv4_address: 198.18.133.6
      username: !vault |
        $ANSIBLE_VAULT;1.1;AES256
        66386439653236336464643261616236636639393866663066353834646436383431353336353939
        6133666132653831396639323234613161333064323534650a333764373233373939376664623332
        38356165656364396136373937303732643938663035646466393963373634636439633665323461
        3832663066623561640a636138383766653031343066346464623534643964343466313330613566
        6161
      password: !vault |
        $ANSIBLE_VAULT;1.1;AES256
        39663933363834613965383565323461396465646533663036386336366633303730396239663965
        6631343035636465653766623937326665373836626461310a333133316465326130663131366234
        66373432393765616137653632346262646138366466396531316465326462633564353032383736
        3031306439383861390a323636316539653063343832343361366463383865663830343632633437
        61313765623134343862643064643430643265396463353736373536396433363034
```

**Important Notes**:
- Keep indentation consistent when pasting encrypted blocks
- VS Code may show warnings about `!vault` - this is normal and valid for Ansible
- The vault password file is required for decryption during playbook execution

**Pros**: Highly secure, encrypted at rest, good for production
**Cons**: More complex setup, requires vault password management

### Step 3: Mixed Environment Example

You can combine different credential methods within the same deployment:

```yaml
# topology_switches.nac.yaml
switches:
  # Production leaf - uses Vault encryption
  - name: leaf-1
    management:
      management_ipv4_address: 198.18.133.1
      username: !vault |
        $ANSIBLE_VAULT;1.1;AES256
        66386439653236336464643...
      password: !vault |
        $ANSIBLE_VAULT;1.1;AES256
        39663933363834613965383...

  # CI/CD leaf - uses environment variables
  - name: leaf-2
    management:
      management_ipv4_address: 198.18.133.2
      username: env_var_leaf2_username
      password: env_var_leaf2_password

  # Test leaf - uses plain text (testing only)
  - name: leaf-3
    management:
      management_ipv4_address: 198.18.133.3
      username: admin
      password: "C1sco!23456"

  # Default leaf - uses group_vars defaults
  - name: leaf-4
    management:
      management_ipv4_address: 198.18.133.4
      # No username/password specified - uses group_vars defaults
```

### Step 4: Execute Your Playbook

**Standard execution**:
```bash
ansible-playbook -i inventory.yaml vxlan_skaszlik-nac-fabric1.yaml
```

**If vault password file not in ansible.cfg**:
```bash
ansible-playbook -i inventory.yaml \
  --vault-password-file /absolute/path/to/vault_password_file \
  vxlan_skaszlik-nac-fabric1.yaml
```

---

## Troubleshooting Common Issues

### Vault Decryption Failed
**Error**: "no vault secrets were found..."

**Solutions**:
- Ensure `vault_password_file` or `vault_identity_list` is correctly set in `ansible.cfg`
- Verify `ANSIBLE_VAULT_PASSWORD_FILE` environment variable is exported
- Check that vault password file contains the correct password and is readable
- Confirm the encrypted content matches the vault password

### Environment Variables Not Recognized
**Error**: Credentials fall back to defaults unexpectedly

**Solutions**:
- Variable names in YAML must exactly match environment variable names (including `env_var_` prefix)
- Quote special characters when exporting: `export env_var_PASSWORD='S3cure$Th!ng'`
- Verify variables are set: `echo $env_var_variablename`
- Ensure variables are exported in the same shell session running Ansible

### Switch Not Found
**Error**: Switch credentials not being applied

**Solutions**:
- Verify `management.management_ipv4_address` matches exactly between topology and credentials
- Check that both `username` and `password` are defined in the switch management section
- Confirm group_vars defaults (`ndfc_switch_username`, `ndfc_switch_password`) are defined

### Vault Interactive Prompt Issues
**Error**: Ansible prompts for vault password interactively

**Root Cause**: The nac_yaml loader cannot handle interactive prompts

**Solutions**:
- Always use non-interactive vault password methods (file or environment variable)
- Avoid `--ask-vault-pass` when using NAC VXLAN collections
- Configure vault password file in `ansible.cfg` or use environment variables

---

## Security Best Practices

### 1. Credential Storage Security
- ❌ **Never commit vault password files** to version control
- ✅ **Add vault password files to `.gitignore`**
- ✅ **Use appropriate file permissions** (`chmod 600` for vault files)
- ✅ **Rotate vault passwords regularly** in production environments

### 2. Environment Variable Security
- ✅ **Use secure environment variable management** in CI/CD systems
- ✅ **Clear sensitive environment variables** after use when possible
- ❌ **Avoid logging environment variables** that contain credentials

### 3. Access Control
- ✅ **Limit access to vault password files** to authorized personnel only
- ✅ **Use separate vault passwords** for different environments (dev/staging/prod)
- ✅ **Implement proper backup and recovery** procedures for vault passwords

### 4. Credential Method Selection
- 🔐 **Production**: Use Ansible Vault for long-term, secure storage
- ✅ **CI/CD**: Use environment variables for automation and flexibility
- ⚠️ **Testing only**: Use plain text only in isolated lab environments

---

## FAQ

### Can I decrypt with just a password (no vault_password_file)?
**Short answer**: No, not interactively.

**Detailed explanation**: The nac_yaml loader invokes `ansible-vault` in a non-interactive subprocess via a `--vault-id` helper script, so it cannot prompt for a password. You must provide the secret non-interactively via one of:
- `vault_password_file` or `vault_identity_list` in `ansible.cfg`
- An environment-based identity (e.g., a command in `vault_identity_list` that echoes a password)
- An environment variable consumed by the helper script used as `--vault-id`

### What happens if I mix credential methods?
The system will use the most specific credentials available for each switch. The resolution order is:
1. Switch-specific credentials (environment variables, vault, or plain text)
2. Group default credentials (fallback)

Each switch is evaluated independently, so you can use different methods for different switches.

### How do I rotate credentials?
- **Environment variables**: Update the environment variable values
- **Vault**: Re-encrypt with new credentials using `ansible-vault encrypt_string`
- **Plain text**: Update the values directly in the YAML (not recommended for production)

### Can I use the same vault password for multiple deployments?
Yes, but for security best practices, consider using separate vault passwords for different environments or deployments to limit blast radius in case of compromise.

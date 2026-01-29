# Switch Discovery Credentials Guide

## Overview

This guide explains how to configure and use different credential types with the NaC VXLAN solution. Understanding the distinction between switch admin credentials, discovery credentials, and ND controller credentials is essential for proper fabric management.

## Credential Types Overview

The NaC VXLAN solution uses three distinct sets of credentials:

1. **ND Controller Credentials (`ND_USERNAME` / `ND_PASSWORD`)**
   - Used to authenticate to Nexus Dashboard / ND controller
   - Required for pushing configuration changes to switches via ND
   - Controller-level authentication

2. **Switch Admin Credentials (`NDFC_SW_USERNAME` / `NDFC_SW_PASSWORD`)**
   - Default admin account on switches (typically `admin` when used with poap or preprovision).

3. **Switch Discovery Account Credentials (optional) (`NDFC_SW_DISCOVERY_USERNAME` / `NDFC_SW_DISCOVERY_PASSWORD`)**
   - If not provided, admin account will be used with `NDFC_SW_USERNAME` / `NDFC_SW_PASSWORD`.

> [!WARNING]
> The minimal length for the password is 8 characters.

## Configuration Steps

### 1. Set Environment Variables

All credential types must be configured as environment variables. These are referenced in the `connection.yaml` file and automatically picked up by the NaC VXLAN framework.

```bash
# NDFC Controller credentials (for API authentication)
export ND_USERNAME="nd_admin"
export ND_PASSWORD="NdAdminPass123!"

# Switch admin credentials (default admin account for POAP/preprovision)
export NDFC_SW_USERNAME="admin"
export NDFC_SW_PASSWORD="Admin123!"

# Switch discovery credentials (service account for ongoing polling)
export NDFC_SW_DISCOVERY_USERNAME="nd-svc-account"
export NDFC_SW_DISCOVERY_PASSWORD="ServiceAccount123!"
```

**Important**: These environment variables are referenced in the `connection.yaml` file and automatically picked up by the NaC VXLAN framework.

#### Environment Variables Reference

| Variable | Purpose | Typical Value | When Used |
|----------|---------|---------------|-----------|
| `ND_USERNAME` | ND controller authentication | `nd_admin` | All API calls to ND |
| `ND_PASSWORD` | ND controller password | `SecurePass123!` | All API calls to ND |
| `NDFC_SW_USERNAME` | Switch admin account (always admin) | `admin` | POAP, pre-provision initial setup |
| `NDFC_SW_PASSWORD` | Switch admin password | `Admin123!` | POAP, pre-provision initial setup |
| `NDFC_SW_DISCOVERY_USERNAME` | Service account for discovery/polling | `nd-svc-account` | Ongoing discovery and monitoring |
| `NDFC_SW_DISCOVERY_PASSWORD` | Service account password | `ServicePass123!` | Ongoing discovery and monitoring |

## Configuration Steps

### 1. Set Environment Variables

Discovery credentials must be configured as environment variables. These credentials should match the credentials configured on the switches during factory reset or initial boot.

```bash
export NDFC_SW_DISCOVERY_USERNAME="admin"
export NDFC_SW_DISCOVERY_PASSWORD="Cisco123!"
```

**Important**: These environment variables are referenced in the `connection.yaml` file and automatically picked up by the NaC VXLAN framework.
All credentials are mapped in the `group_vars/ndfc/connection.yaml` file:

```yaml
# Connection Parameters for 'nd' inventory group

# ND Controller credentials (for API authentication)
nd_username: "{{ lookup('env', 'ND_USERNAME') }}"
nd_password: "{{ lookup('env', 'ND_PASSWORD') }}"

# Switch admin credentials (for POAP/preprovision initial setup)
ndfc_switch_username: "{{ lookup('env', 'NDFC_SW_USERNAME') }}"
ndfc_switch_password: "{{ lookup('env', 'NDFC_SW_PASSWORD') }}"

# Switch discovery credentials (for ongoing polling and discovery)
ndfc_switch_discovery_username: "{{ lookup('env', 'NDFC_SW_DISCOVERY_USERNAME') }}"
ndfc_switch_discovery_password: "{{ lookup('env', 'NDFC_SW_DISCOVERY_PASSWORD') }}"
```

Configure switches to use discovery credentials, set the `discovery_creds: true` flag in your switch configuration within the `topology_switches.nac.yaml` file:

```yaml
vxlan:
  topology:
    switches:
      - name: netascode-leaf-01
        role: leaf
        serial_number: FDO12345678
        management:
          default_gateway_v4: 10.10.10.1
          management_ipv4_address: 10.10.10.101
          subnet_mask_ipv4: 24
        poap:
          bootstrap: false
          discovery_creds: true  # Use discovery credentials for ongoing polling
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

### 4. Configure AAA Remote Credential Passthrough (Recommended)

When using the same service account for ND controller access (`ND_USERNAME`) and switch discovery (`NDFC_SW_DISCOVERY_USERNAME`), you should enable **AAA Remote Credential Passthrough** in ND. This feature automatically propagates credentials to switches without manual configuration.

**Benefits:**
- Automatically sets LAN credentials on switches
- Eliminates manual credential management
- Ensures consistency across fabric
- Simplifies remote authentication integration

**Configuration Steps 3.2:**

1. Log in to ND Web UI
2. Navigate to **Fabric Controller → Admin → Server Settings**
3. Under **LAN Credentials**, enable **AAA Passthrough feature**
4. Save configuration

**Configuration Steps 4.1:**

1. Log in to ND Web UI
2. Navigate to **Admin → System Settings → Fabric Management**
3. Under **Management**, enable **AAA Passthrough of device credentials**
4. Save configuration

**Reference Documentation:**
- [ND Overview and Initial Setup - Server Settings 3.2](https://www.cisco.com/c/en/us/td/docs/dcn/ndfc/1222/articles/ndfc-overview-initial-setup-lan/overview-and-initial-setup-of-ndfc-lan.html#_server_settings)
- [ND Overview and Initial Setup - Server Settings 4.1](https://www.cisco.com/c/en/us/td/docs/dcn/nd/4x/articles-411/working-with-system-settings.html#_fabric_management)
- [ND Managing your device credentials](https://www.cisco.com/c/en/us/td/docs/dcn/nd/4x/articles-411/managing-your-device-credentials.html)

## Examples

### Discovery Credentials Priority Order

When `discovery_creds: true` is enabled in the POAP configuration, the system follows a priority order to resolve which credentials to use.

#### Important Clarification
**Environment Variables and Group Variables are interconnected**: The `group_vars/ndfc/connection.yaml` file uses `lookup('env', ...)` to populate group variables from environment variables. They are not separate priority levels, but rather the same source accessed in different ways.

```yaml
# In group_vars/ndfc/connection.yaml
ndfc_switch_discovery_username: "{{ lookup('env', 'NDFC_SW_DISCOVERY_USERNAME') }}"
ndfc_switch_discovery_password: "{{ lookup('env', 'NDFC_SW_DISCOVERY_PASSWORD') }}"
```

#### Priority Resolution (Highest to Lowest)
1. **Switch-Specific Credentials** - Individual `discovery_username` and `discovery_password` defined in the switch's POAP configuration
   - Can be plain text values
   - Can be Ansible Vault encrypted values
   - Can reference environment variables using `env_var_` prefix (e.g., `env_var_MY_PASSWORD`)
   - If `env_var_` prefix is used but environment variable not found, falls back to group_vars credentials

2. **Global Group Variables / Environment Variables** - `ndfc_switch_discovery_username` and `ndfc_switch_discovery_password` from `group_vars/ndfc/connection.yaml`
   - These are populated from `NDFC_SW_DISCOVERY_USERNAME` and `NDFC_SW_DISCOVERY_PASSWORD` environment variables
   - Used when no switch-specific credentials are defined

#### Resolution Example Flow
```
If switch has discovery_username/password defined:
  ├─ Check if value starts with 'env_var_' prefix:
  │  ├─ If yes: Try to resolve from environment variable
  │  │           ├─ If found: Use it (Priority 1a)
  │  │           └─ If not found: Fall back to group_vars (Priority 2)
  │  └─ If no: Use the value directly (Priority 1b)
  └─ Done

Else if switch does NOT have switch-specific credentials:
  ├─ Use group_vars credentials (Priority 2)
  │  (which were populated from NDFC_SW_DISCOVERY_USERNAME/PASSWORD env vars)
  └─ Done

Else (no switch-specific AND no group_vars credentials):
  ├─ FAIL with error message
  └─ Playbook execution stops (retrieve_failed = True)
```

#### ⚠️ Important: Failure Behavior

**If `discovery_creds: true` is set but NO credentials are found**, the playbook will **FAIL**:

```
retrieve_failed: True
failed: True
msg: "Discovery credentials incomplete for device {device_ip}. Ensure global discovery credentials are set."
```

**To avoid this failure, you MUST either:**
- Define individual `discovery_username` and `discovery_password` in the switch POAP configuration, OR
- Configure the global environment variables `NDFC_SW_DISCOVERY_USERNAME` and `NDFC_SW_DISCOVERY_PASSWORD` (which populate group_vars)

### Example Configurations

Additionally, we can configure directly discovery credential per switch using key discover_username and discover_password.

**Not recommended in production with plain text**

```
vxlan:
  topology:
    switches:
      - name: netascode-leaf-01
        role: leaf
        serial_number: FDO12345678
        management:
          default_gateway_v4: 10.10.10.1
          management_ipv4_address: 10.10.10.101
          subnet_mask_ipv4: 24
        poap:
          bootstrap: false
          discovery_creds: true  # Enable discovery credentials
          discovery_username: svc_account
          discvoery_password: cisco1234
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

**Using Ansible Vault**

```
vxlan:
  topology:
    switches:
      - name: netascode-leaf-01
        role: leaf
        serial_number: FDO12345678
        management:
          default_gateway_v4: 10.10.10.1
          management_ipv4_address: 10.10.10.101
          subnet_mask_ipv4: 24
        poap:
          bootstrap: false
          discovery_creds: true  # Enable discovery credentials
          discovery_username: svc_account
          discovery_password: !vault |
              $ANSIBLE_VAULT;1.1;AES256
              63386330333766383135353230346633373936613261373334306666336436303435336338363335
              3361376436336134363865633864313033643439633964350a623536396165303431316366336135
              61363233343334376231663937313234306538323766326538313332626238663338386534633038
              6333326263363565620a636334303336616361646535393332306465616535616536353933396564
              6231
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

**Using environment variables starting by `env_var_`**

```
vxlan:
  topology:
    switches:
      - name: netascode-leaf-01
        role: leaf
        serial_number: FDO12345678
        management:
          default_gateway_v4: 10.10.10.1
          management_ipv4_address: 10.10.10.101
          subnet_mask_ipv4: 24
        poap:
          bootstrap: false
          discovery_creds: true  # Enable discovery credentials
          discovery_username: svc_account
          discovery_password: env_var_netascode-leaf-01_password
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

**Using global common environment in the group_vars**

```yaml
# When using same service account for ND and discovery
# With AAA Remote Credential Passthrough enabled

# ND Controller and Discovery use same account
export ND_USERNAME="nd-svc-account"
export ND_PASSWORD="ServiceAccount123!"
export NDFC_SW_DISCOVERY_USERNAME="nd-svc-account"
export NDFC_SW_DISCOVERY_PASSWORD="ServiceAccount123!"

# Switch admin remains separate (always admin) with POAP
export NDFC_SW_USERNAME="admin"
export NDFC_SW_PASSWORD="Admin123!"

vxlan:
  topology:
    switches:
      - name: netascode-leaf-01
        role: leaf
        serial_number: FDO12345678
        management:
          default_gateway_v4: 10.10.10.1
          management_ipv4_address: 10.10.10.101
          subnet_mask_ipv4: 24
        poap:
          bootstrap: false
          discovery_creds: true  # Enable discovery credentials
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

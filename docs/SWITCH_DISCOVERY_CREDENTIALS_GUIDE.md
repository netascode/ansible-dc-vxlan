# Switch Discovery Credentials Guide

## Overview

This guide explains how to configure and use different credential types with the NaC VXLAN solution. Understanding the distinction between switch admin credentials, discovery credentials, and NDFC controller credentials is essential for proper fabric management.

## Credential Types Overview

The NaC VXLAN solution uses three distinct sets of credentials:

1. **NDFC Controller Credentials (`ND_USERNAME` / `ND_PASSWORD`)**
   - Used to authenticate to Nexus Dashboard / NDFC controller
   - Required for pushing configuration changes to switches via NDFC
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
export ND_USERNAME="ndfc_admin"
export ND_PASSWORD="NdfcAdminPass123!"

# Switch admin credentials (default admin account for POAP/preprovision)
export NDFC_SW_USERNAME="admin"
export NDFC_SW_PASSWORD="Admin123!"

# Switch discovery credentials (service account for ongoing polling)
export NDFC_SW_DISCOVERY_USERNAME="ndfc-svc-account"
export NDFC_SW_DISCOVERY_PASSWORD="ServiceAccount123!"
```

**Important**: These environment variables are referenced in the `connection.yaml` file and automatically picked up by the NaC VXLAN framework.

#### Environment Variables Reference

| Variable | Purpose | Typical Value | When Used |
|----------|---------|---------------|-----------|
| `ND_USERNAME` | NDFC controller authentication | `ndfc_admin` | All API calls to NDFC |
| `ND_PASSWORD` | NDFC controller password | `SecurePass123!` | All API calls to NDFC |
| `NDFC_SW_USERNAME` | Switch admin account (always admin) | `admin` | POAP, pre-provision initial setup |
| `NDFC_SW_PASSWORD` | Switch admin password | `Admin123!` | POAP, pre-provision initial setup |
| `NDFC_SW_DISCOVERY_USERNAME` | Service account for discovery/polling | `ndfc-svc-account` | Ongoing discovery and monitoring |
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
# Connection Parameters for 'ndfc' inventory group

# NDFC Controller credentials (for API authentication)
nd_username: "{{ lookup('env', 'ND_USERNAME') }}"
nd_password: "{{ lookup('env', 'ND_PASSWORD') }}"

# Switch admin credentials (for POAP/preprovision initial setup)
ndfc_switch_username: "{{ lookup('env', 'NDFC_SW_USERNAME') }}"
ndfc_switch_password: "{{ lookup('env', 'NDFC_SW_PASSWORD') }}"

# Switch discovery credentials (for ongoing polling and discovery)
ndfc_switch_discovery_username: "{{ lookup('env', 'NDFC_SW_DISCOVERY_USERNAME') }}"
ndfc_switch_discovery_password: "{{ lookup('env', 'NDFC_SW_DISCOVERY_PASSWORD') }}"
```

Configure switches to use discovery credentials for ongoing monitoring, set the `discovery_new_user: true` flag in your switch configuration within the `topology_switches.nac.yaml` file:

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
          discovery_new_user: true  # Use discovery credentials for ongoing polling
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

### 4. Configure AAA Remote Credential Passthrough (Recommended)

When using the same service account for NDFC controller access (`ND_USERNAME`) and switch discovery (`NDFC_SW_DISCOVERY_USERNAME`), you should enable **AAA Remote Credential Passthrough** in NDFC. This feature automatically propagates credentials to switches without manual configuration.

**Benefits:**
- Automatically sets LAN credentials on switches
- Eliminates manual credential management
- Ensures consistency across fabric
- Simplifies remote authentication integration

**Configuration Steps 3.2:**

1. Log in to NDFC Web UI
2. Navigate to **Fabric Controller → Admin → Server Settings**
3. Under **LAN Credentials**, enable **AAA Passthrough feature**
4. Save configuration

**Configuration Steps 4.1:**

1. Log in to NDFC Web UI
2. Navigate to **Admin → System Settings → Fabric Management**
3. Under **Management**, enable **AAA Passthrough of device credentials**
4. Save configuration

**Reference Documentation:**
- [NDFC Overview and Initial Setup - Server Settings 3.2](https://www.cisco.com/c/en/us/td/docs/dcn/ndfc/1222/articles/ndfc-overview-initial-setup-lan/overview-and-initial-setup-of-ndfc-lan.html#_server_settings)
- [NDFC Overview and Initial Setup - Server Settings 4.1](https://www.cisco.com/c/en/us/td/docs/dcn/nd/4x/articles-411/working-with-system-settings.html#_fabric_management)

## Example

```yaml
# When using same service account for ND and discovery
# With AAA Remote Credential Passthrough enabled

# NDFC Controller and Discovery use same account
export ND_USERNAME="ndfc-svc-account"
export ND_PASSWORD="ServiceAccount123!"
export NDFC_SW_DISCOVERY_USERNAME="ndfc-svc-account"
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
          discovery_new_user: true  # Enable discovery credentials
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

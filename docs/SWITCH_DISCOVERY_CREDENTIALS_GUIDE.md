# Switch Discovery Credentials Guide

## Overview

This guide explains how to set and use different credential types with the NaC VXLAN solution for switch discovery with POAP. 
Understanding the distinction between switch admin credentials and discovery credentials is essential for proper fabric management.

| Action | Admin Credentials | Discovery Credentials |
|----------|----------|----------|
| Access | Read-Write | Read-Only |
| Use | Configuration Changes | Inventory |
| Protocols | SSH | SSH & SNMPv3 |

> [!NOTE]
> In the absense of discovery credentials, admin credentials are used for both actions.

## Credential Types

The NaC VXLAN solution uses distinct sets of credentials:

**Admin Credentials** 

Admin credentials are the admin account on switches (typically `admin` when used with POAP or preprovision).
These are set one of two ways:
- In group_vars for all switches
- As a per switch override

**group_vars**
   - The variables in group_vars are: `ndfc_switch_username` and `ndfc_switch_username`
   - The environment variables `NDFC_SW_USERNAME` and `NDFC_SW_PASSWORD` can we set and used as in the example below:

```yaml
# In group_vars/nd/connection.yaml

# Switch admin credentials (for POAP/preprovision initial setup)
ndfc_switch_username: "{{ lookup('env', 'NDFC_SW_USERNAME') }}"
ndfc_switch_password: "{{ lookup('env', 'NDFC_SW_PASSWORD') }}"
```
**Per Switch**

Admin credentials have a per switch override for each in the data model:

```yaml
vxlan:
  topology:
    switches:
      - name: nac-s1-leaf1
        serial_number: 9C2MQTWVJXA
        role: leaf
        management:
          default_gateway_v4: 10.15.33.1
          management_ipv4_address: 10.15.33.13
          username: env_var_leaf2_username
          password: env_var_leaf2_password
```

More information can be found in the [topology switches](https://netascode.cisco.com/docs/data_models/vxlan/topology/topology_switch/) section of the model as well as the [switch credentials documentation guide](https://github.com/netascode/ansible-dc-vxlan/blob/main/docs/SWITCH_CREDENTIALS_GUIDE.md).


**Discovery Credentials**

**`ndfc_switch_discovery_username` / `ndfc_switch_discovery_password`**

```yaml
# In group_vars/ndfc/connection.yaml

# Switch discovery credentials (for ongoing polling and discovery)
ndfc_switch_discovery_username: "{{ lookup('env', 'NDFC_SW_DISCOVERY_USERNAME') }}"
ndfc_switch_discovery_password: "{{ lookup('env', 'NDFC_SW_DISCOVERY_PASSWORD') }}"
```
`NDFC_SW_DISCOVERY_USERNAME` / `NDFC_SW_DISCOVERY_PASSWORD`

**Local account** defined under switch:

1.  **Switch Admin Credentials (`username`/`password`)**

```yaml
---
vxlan:
  topology:
    switches:
      - name: leaf-1
        management:
          management_ipv4_address: 198.18.133.3
          username: admin
          password: "C1sco!23456"
```

2. **Switch Discovery Account Credentials (optional) (`discovery_username`/`discovery_password`)**

> [!WARNING]
> `discovery_creds` controls if you want to use or not discovery credentials. For example if `NDFC_SW_DISCOVERY_USERNAME` / `NDFC_SW_DISCOVERY_PASSWORD` is defined under `group_vars` but you don't want use discovery for one switch set `discovery_creds` to `false` which is the default value.

```yaml
---
vxlan:
  topology:
    switches:
      - name: leaf-1
        management:
          management_ipv4_address: 198.18.133.3
          username: admin
          password: "C1sco!23456"
        poap:
          bootstrap: false
          discovery_creds: true  # Enable discovery credentials
          discovery_username: svc_account
          discovery_password: cisco1234
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

> [!WARNING]
> Local account is always preferred when both Global and Local accounts are configured.

> [!WARNING]
> The minimal length for the password is 8 characters.

## Configuration Steps

### 1. Set Environment Global Variables

All credential types must be configured as environment variables. These are referenced in the `connection.yaml` file and automatically picked up by the NaC VXLAN framework.

**Environment Variables and Group Variables are interconnected**: The `group_vars/ndfc/connection.yaml` file uses `lookup('env', ...)` to populate group variables from environment variables. They are not separate priority levels, but rather the same source accessed in different ways.

```yaml
# In group_vars/ndfc/connection.yaml

# Switch admin credentials (for POAP/preprovision initial setup)
ndfc_switch_username: "{{ lookup('env', 'NDFC_SW_USERNAME') }}"
ndfc_switch_password: "{{ lookup('env', 'NDFC_SW_PASSWORD') }}"

# Switch discovery credentials (for ongoing polling and discovery)
ndfc_switch_discovery_username: "{{ lookup('env', 'NDFC_SW_DISCOVERY_USERNAME') }}"
ndfc_switch_discovery_password: "{{ lookup('env', 'NDFC_SW_DISCOVERY_PASSWORD') }}"
```

```shell
# Switch admin credentials (default admin account for POAP/preprovision)
export NDFC_SW_USERNAME="admin"
export NDFC_SW_PASSWORD="Admin123!"

# Switch discovery credentials (service account for ongoing polling)
export NDFC_SW_DISCOVERY_USERNAME="nd-svc-account"
export NDFC_SW_DISCOVERY_PASSWORD="ServiceAccount123!"
```

#### Environment Variables Reference

| Variable | Purpose | Typical Value |
|----------|---------|---------------|
| `NDFC_SW_USERNAME` | Switch admin account (always admin) | `admin` |
| `NDFC_SW_PASSWORD` | Switch admin password | `Admin123!` |
| `NDFC_SW_DISCOVERY_USERNAME` | Service account for discovery/polling | `nd-svc-account` |
| `NDFC_SW_DISCOVERY_PASSWORD` | Service account password | `ServicePass123!` |


### 2. Configure AAA Remote Credential Passthrough (Recommended)

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

### Example1 - POAP with Global admin/password, no discovery account

* **Global variables `NDFC_SW_USERNAME`/`NDFC_SW_PASSWORD` set without discovery**
* **Local variables `username`/`password` are NOT set, `discovery_creds` is `false`.**

In that case, we will discover the switch using admin credentials under group_vars

```yaml
---
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
          discovery_creds: false  # Enable discovery credentials
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

### Example2 - POAP with Global admin/password + Local admin/password

* **Global variables `NDFC_SW_USERNAME`/`NDFC_SW_PASSWORD` set without discovery**
* **Local variables `username`/`password` are set, `discovery_creds` is `false`.**

In that case, we will discover the switch using admin credentials under local. Local is always preferred.

```yaml
---
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
          username: admin
          password: cisco1234
        poap:
          bootstrap: false
          discovery_creds: false  # Enable discovery credentials
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

### Example3 - POAP with Global admin/password + Local admin/password + Global Discovery account

* **Global variables `NDFC_SW_USERNAME`/`NDFC_SW_PASSWORD` set with `NDFC_SW_DISCOVERY_USERNAME`/`NDFC_SW_DISCOVERY_PASSWORD` discovery**
* **Local variables `username`/`password` are set, `discovery_creds` is `false`.**

In that case, we will discover the switch using admin credentials (`username`/`password`) under local. Even if a discovery account is defined in group_vars, we will NOT use it because `discovery_creds` is false.

```yaml
---
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
          username: admin
          password: cisco1234
        poap:
          bootstrap: false
          discovery_creds: false  # Enable discovery credentials
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

### Example4 - POAP with Global admin/password + Local admin/password + Global Discovery account

* **Global variables `NDFC_SW_USERNAME`/`NDFC_SW_PASSWORD` set with `NDFC_SW_DISCOVERY_USERNAME`/`NDFC_SW_DISCOVERY_PASSWORD` discovery**
* **Local variables `username`/`password` are set, `discovery_creds` is `true`.**

In that case, we will discover the switch using Global discovery credentials and use `password` for the admin password.

```yaml
---
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
          username: admin
          password: cisco1234
        poap:
          bootstrap: false
          discovery_creds: true  # Enable discovery credentials
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

### Example5 - POAP with Global admin/password + Local admin/password + Global Discovery account + Local Discovery Account

* **Global variables `NDFC_SW_USERNAME`/`NDFC_SW_PASSWORD` set with `NDFC_SW_DISCOVERY_USERNAME`/`NDFC_SW_DISCOVERY_PASSWORD` discovery**
* **Local variables `username`/`password` and `discovery_username`/`discovery_password` are set, `discovery_creds` is `true`.**

In that case, we will discover the switch using Local discovery credentials and use `password` for the admin password.

```yaml
---
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
          username: admin
          password: cisco1234
        poap:
          bootstrap: false
          discovery_creds: true  # Enable discovery credentials
          discovery_username: svc_account
          discovery_password: cisco1234
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

### Example6 - POAP with Global admin/password + Local admin/password + Global Discovery account + Local Discovery Account

* **Global variables `NDFC_SW_USERNAME`/`NDFC_SW_PASSWORD` set with `NDFC_SW_DISCOVERY_USERNAME`/`NDFC_SW_DISCOVERY_PASSWORD` discovery**
* **Local variables `username`/`password` and `discovery_username`/`discovery_password` are set, `discovery_creds` is `false`.**

In that case, we will discover the switch using Local `username`/`password` credentials, because `discovery_creds` is `false`.

```yaml
---
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
          username: admin
          password: cisco1234
        poap:
          bootstrap: false
          discovery_creds: false  # Enable discovery credentials
          discovery_username: svc_account
          discovery_password: cisco1234
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

#### ⚠️ Important: Failure Behavior

**when `discovery_creds: true` is set but NO credentials are found**, the playbook will **FAIL**, because discovery account is expected:

```shell
retrieve_failed: True
failed: True
msg: "Discovery credentials incomplete for device {device_ip}. Ensure global discovery credentials are set."
```

**To avoid this failure, you MUST either:**
- Define individual `discovery_username` and `discovery_password` in the switch POAP configuration, OR
- Configure the global environment variables `NDFC_SW_DISCOVERY_USERNAME` and `NDFC_SW_DISCOVERY_PASSWORD` (which populate group_vars)

## Securing Switch Credentials

In the following examples, we use `discovery_username`/`discovery_password` in clear text. You can use Ansible Vault or environment variables to secure credentials.

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
          discovery_creds: true  # Enable discovery credentials
          discovery_username: svc_account
          discovery_password: cisco1234
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

**Secure using Ansible Vault**

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

**Secure using environment variables starting with `env_var_`**

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
          discovery_creds: true  # Enable discovery credentials
          discovery_username: svc_account
          discovery_password: env_var_netascode-leaf-01_password
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

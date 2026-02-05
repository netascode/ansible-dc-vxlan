# Switch Discovery Credentials Guide

## Overview

This guide explains how to set and use different credential types with the NaC VXLAN solution for switch discovery with POAP. 
Understanding the distinction between switch admin credentials and discovery credentials is essential for proper fabric management.

| Action | Device Credentials | Discovery Credentials |
|----------|----------|----------|
| Access | Read-Write | Read-Only |
| Use | Configuration Changes | Inventory |
| Protocols | SSH | SSH & SNMPv3 |

> [!NOTE]
> In the absense of discovery credentials, admin credentials are used for both actions.

> [!WARNING]
> The minimal length for the password is 8 characters.

## Credential Types

The NaC VXLAN solution uses distinct sets of credentials:

### Device Credentials

Admin credentials are the admin account (network-admin) on switches (typically `admin` when used with POAP or preprovision).
These are set one of two ways:
- Ansible group variables under the well-known group_vars (applies for all switches)
- As a per switch override in the data model

**Ansible Group Variables**
   - The variables in group_vars are: `ndfc_switch_username` and `ndfc_switch_username`
   - The environment variables `NDFC_SW_USERNAME` and `NDFC_SW_PASSWORD` can be set and used as in the example below:

```yaml
# In group_vars/nd/connection.yaml

# Switch admin credentials (for POAP/preprovision initial setup)
ndfc_switch_username: "{{ lookup('env', 'NDFC_SW_USERNAME') }}"
ndfc_switch_password: "{{ lookup('env', 'NDFC_SW_PASSWORD') }}"
```

**Per Switch Credentials in Data Model**

Admin credentials have a per switch override for each in the data model:

```yaml
vxlan:
  topology:
    switches:
      - name: nac-leaf1
        serial_number: 9C2MQTWVJXA
        role: leaf
        management:
          default_gateway_v4: 10.15.33.1
          management_ipv4_address: 10.15.33.13
          username: env_var_leaf1_username
          password: env_var_leaf1_password
```

More information can be found in the [topology switches](https://netascode.cisco.com/docs/data_models/vxlan/topology/topology_switch/) section of the model as well as the [switch credentials documentation guide](https://github.com/netascode/ansible-dc-vxlan/blob/main/docs/SWITCH_CREDENTIALS_GUIDE.md).

### Discovery Credentials

Discovery credentials are used for device discovery of switches.
These are set one of two ways:
- Ansible group variables under the well-known group_vars (applies for all switches)
- As a per switch override in the data model

> [!NOTE]
> `discovery_creds` controls if you want to use discovery credentials at all either using the environment variables or per-switch discovery credentials.

**Ansible Group Variables**
   - The variables in group_vars are: `ndfc_switch_discovery_username` and `ndfc_switch_discovery_password`
   - The environment variables `NDFC_SW_DISCOVERY_USERNAME` and `NDFC_SW_DISCOVERY_PASSWORD` can be set and used as in the example below:

```yaml
# In group_vars/nd/connection.yaml

# Switch discovery credentials (for ongoing polling and discovery)
ndfc_switch_discovery_username: "{{ lookup('env', 'NDFC_SW_DISCOVERY_USERNAME') }}"
ndfc_switch_discovery_password: "{{ lookup('env', 'NDFC_SW_DISCOVERY_PASSWORD') }}"
```

**Per Switch POAP Discovery Credentials in Data Model**

Discovery credentials per switch override for each in the data model:

```yaml
---
vxlan:
  topology:
    switches:
      - name: nac-leaf1
        serial_number: 9C2MQTWVJXA
        role: leaf
        management:
          default_gateway_v4: 10.15.33.1
          management_ipv4_address: 10.15.33.13
          username: env_var_leaf1_username
          password: env_var_leaf1_password
        poap:
          bootstrap: true
          discovery_creds: true  # Enable discovery credentials
          discovery_username: service_acct
          discovery_password: cisco.1234
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

## Enable AAA Remote Credential Passthrough (Recommended)

When using the same service account for Nexus Dashboard (`ND_USERNAME`) and switch discovery (`NDFC_SW_DISCOVERY_USERNAME`), you should enable **AAA Remote Credential Passthrough**. This feature automatically propagates credentials to switches without manual configuration.

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

### POAP with Global Device Credentials Env Var (No Discovery Credentials)

In this scenario, you will discover the switch using device credentials under group_vars.

The following credentials are set:
* `ndfc_switch_username` and `ndfc_switch_password`

>[!NOTE]
>You can set the `NDFC_SW_USERNAME` and `NDFC_SW_PASSWORD` environment variables to the group vars values

Group vars:

```yaml
# In group_vars/nd/connection.yaml

# Switch admin credentials (for POAP/preprovision initial setup)
ndfc_switch_username: "{{ lookup('env', 'NDFC_SW_USERNAME') }}"
ndfc_switch_password: "{{ lookup('env', 'NDFC_SW_PASSWORD') }}"
```

Switch definition:

>[!NOTE]
>If any discovery credentials are set, they are ignored as the `discovery_creds` parameter is `false`

```yaml
---
vxlan:
  topology:
    switches:
      - name: nac-leaf1
        role: leaf
        serial_number: FDO12345678
        management:
          default_gateway_v4: 10.15.33.1
          management_ipv4_address: 10.15.33.13
          subnet_mask_ipv4: 24
        poap:
          bootstrap: false
          discovery_creds: false  # Enable discovery credentials is false or can be missing from the data model
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

### POAP with Per-Switch Device Credentials (No Discovery Credentials)

In this scenario, you will discover the switch using local, per-switch device credentials.

The following credentials are set:
* `ndfc_switch_username` and `ndfc_switch_password`
* Per-switch `username` and `password`

>[!NOTE]
>You can set the `NDFC_SW_USERNAME` and `NDFC_SW_PASSWORD` environment variables to the group vars values

Group vars:

```yaml
# In group_vars/nd/connection.yaml

# Switch admin credentials (for POAP/preprovision initial setup)
ndfc_switch_username: "{{ lookup('env', 'NDFC_SW_USERNAME') }}"
ndfc_switch_password: "{{ lookup('env', 'NDFC_SW_PASSWORD') }}"
```

Switch definition with per-switch credential:

>[!NOTE]
>The per-switch `username` and `password` override the group_vars variables.

>[!NOTE]
>If any discovery credentials are set, they are ignored as the `discovery_creds` parameter is `false`

```yaml
---
vxlan:
  topology:
    switches:
      - name: nac-leaf1
        role: leaf
        serial_number: FDO12345678
        management:
          default_gateway_v4: 10.15.33.1
          management_ipv4_address: 10.15.33.13
          subnet_mask_ipv4: 24
          username: admin
          password: cisco.123
        poap:
          bootstrap: false
          discovery_creds: false  # Enable discovery credentials is false or can be missing from the data model
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

### POAP with Global Device and Global Discovery Credentials

In this scenario, you will discover the switch using the device discovery credentials under group vars values device credentials will also use group vars values.

The following credentials are set:
* `ndfc_switch_username` and `ndfc_switch_password`
* `ndfc_switch_discovery_username` and `ndfc_switch_discovery_password`

Group vars:

```yaml
# In group_vars/nd/connection.yaml

# Switch discovery credentials (for ongoing polling and discovery)
ndfc_switch_discovery_username: "{{ lookup('env', 'NDFC_SW_DISCOVERY_USERNAME') }}"
ndfc_switch_discovery_password: "{{ lookup('env', 'NDFC_SW_DISCOVERY_PASSWORD') }}"
# Switch discovery credentials (for ongoing polling and discovery)
ndfc_switch_discovery_username: "{{ lookup('env', 'NDFC_SW_DISCOVERY_USERNAME') }}"
ndfc_switch_discovery_password: "{{ lookup('env', 'NDFC_SW_DISCOVERY_PASSWORD') }}"
```

Switch definitiion:

>[!NOTE]
>`discovery_creds` parameter is now `true`

```yaml
---
vxlan:
  topology:
    switches:
      - name: nac-leaf1
        role: leaf
        serial_number: FDO12345678
        management:
          default_gateway_v4: 10.15.33.1
          management_ipv4_address: 10.15.33.13
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

### POAP with Per-Switch Device Credentials and Global Discovery Credentials

In this scenario, you will discover the switch using the device discovery credentials under group vars values but device credentials will use per-switch credentials.

The following credentials are set:
* `ndfc_switch_username` and `ndfc_switch_password`
* Per-switch `username` and `password`
* `ndfc_switch_discovery_username` and `ndfc_switch_discovery_password`

Group vars:

```yaml
# In group_vars/nd/connection.yaml

# Switch discovery credentials (for ongoing polling and discovery)
ndfc_switch_discovery_username: "{{ lookup('env', 'NDFC_SW_DISCOVERY_USERNAME') }}"
ndfc_switch_discovery_password: "{{ lookup('env', 'NDFC_SW_DISCOVERY_PASSWORD') }}"
# Switch discovery credentials (for ongoing polling and discovery)
ndfc_switch_discovery_username: "{{ lookup('env', 'NDFC_SW_DISCOVERY_USERNAME') }}"
ndfc_switch_discovery_password: "{{ lookup('env', 'NDFC_SW_DISCOVERY_PASSWORD') }}"
```

Switch definitiion:

>[!NOTE]
>`discovery_creds` parameter is now `true`

```yaml
---
vxlan:
  topology:
    switches:
      - name: nac-leaf1
        role: leaf
        serial_number: FDO12345678
        management:
          default_gateway_v4: 10.15.33.1
          management_ipv4_address: 10.15.33.13
          subnet_mask_ipv4: 24
          username: admin
          password: cisco.123
        poap:
          bootstrap: false
          discovery_creds: true  # Enable discovery credentials
          preprovision:
            serial_number: FDO12345678
            model: N9K-C93180YC-EX
            version: 10.4(2)
            modulesModel: [N9K-X9364v]
```

### POAP with Per-Switch Device Credentials and Per-Switch Discovery Credentials

In this scenario, you will discover the switch using the device discovery credentials per-switch and device credentials will use per-switch credentials.

The following credentials are set:
* `ndfc_switch_username` and `ndfc_switch_password`
* Per-switch `username` and `password`
* `ndfc_switch_discovery_username` and `ndfc_switch_discovery_password`
* Per-switch `discovery_username` and `discovery_password`

Group vars:

```yaml
# In group_vars/nd/connection.yaml

# Switch discovery credentials (for ongoing polling and discovery)
ndfc_switch_discovery_username: "{{ lookup('env', 'NDFC_SW_DISCOVERY_USERNAME') }}"
ndfc_switch_discovery_password: "{{ lookup('env', 'NDFC_SW_DISCOVERY_PASSWORD') }}"
# Switch discovery credentials (for ongoing polling and discovery)
ndfc_switch_discovery_username: "{{ lookup('env', 'NDFC_SW_DISCOVERY_USERNAME') }}"
ndfc_switch_discovery_password: "{{ lookup('env', 'NDFC_SW_DISCOVERY_PASSWORD') }}"
```

Switch definitiion:

>[!NOTE]
>`discovery_creds` parameter is now `true`

```yaml
---
vxlan:
  topology:
    switches:
      - name: nac-leaf1
        role: leaf
        serial_number: FDO12345678
        management:
          default_gateway_v4: 10.15.33.1
          management_ipv4_address: 10.15.33.13
          subnet_mask_ipv4: 24
          username: admin
          password: cisco.123
        poap:
          bootstrap: false
          discovery_creds: true  # Enable discovery credentials
          discovery_username: service_acct
          discovery_password: cisco.1234
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

# Switch Discovery Authentication Protocol Guide

## Overview

This guide explains how to configure `auth_proto` — the SNMPv3 authentication and privacy
protocol that ND uses when discovering a switch for the first time.

> [!NOTE]
> This guide covers **normal initial switch discovery** (switches already reachable by IP).
> For POAP and preprovision flows, see [SWITCH_DISCOVERY_CREDENTIALS_GUIDE.md](./SWITCH_DISCOVERY_CREDENTIALS_GUIDE.md).

## What auth_proto Controls

When ND discovers a switch, it uses SNMPv3 to test reachability and gather inventory.
`auth_proto` selects the authentication and privacy algorithms for that SNMPv3 session.

The field is set in the data model under `vxlan.global` or `vxlan.multisite.isn`,
depending on the fabric type:

| Fabric type | Data model path |
|---|---|
| VXLAN EVPN (iBGP) | `vxlan.global.ibgp.auth_proto` |
| VXLAN EVPN (eBGP) | `vxlan.global.ebgp.auth_proto` |
| External | `vxlan.global.external.auth_proto` |
| ISN | `vxlan.multisite.isn.auth_proto` |

### Supported Values

| Value | Authentication | Privacy | Default | NX-OS `snmp-server user` arguments |
|---|---|---|---|---|
| `MD5` | MD5 | — | ✓ | `auth md5 <PASSWORD>` |
| `SHA` | SHA-1 | — | | `auth sha <PASSWORD>` |
| `MD5_DES` | MD5 | DES | | `auth md5 <PASSWORD> priv des <PASSWORD>` |
| `MD5_AES` | MD5 | AES-128 | | `auth md5 <PASSWORD> priv aes-128 <PASSWORD>` |
| `SHA_DES` | SHA-1 | DES | | `auth sha <PASSWORD> priv des <PASSWORD>` |
| `SHA_AES` | SHA-1 | AES-128 | | `auth sha <PASSWORD> priv aes-128 <PASSWORD>` |

## Prerequisites

Before running NaC with a non-default `auth_proto`, two prerequisites must be satisfied.

### 1. NX-OS: SNMPv3 user configuration

The SNMPv3 user must exist on every switch with authentication and privacy algorithms
that match the selected `auth_proto`. Create the local user once, then apply the single
`snmp-server user` line for your chosen value:

```
username <USERNAME> password <PASSWORD> role network-admin

! Apply ONE of the following, matching the auth_proto value

! MD5 (default) — authentication only
snmp-server user <USERNAME> network-admin auth md5 <PASSWORD>

! SHA — authentication only
snmp-server user <USERNAME> network-admin auth sha <PASSWORD>

! MD5_DES
snmp-server user <USERNAME> network-admin auth md5 <PASSWORD> priv des <PASSWORD>

! MD5_AES
snmp-server user <USERNAME> network-admin auth md5 <PASSWORD> priv aes-128 <PASSWORD>

! SHA_DES
snmp-server user <USERNAME> network-admin auth sha <PASSWORD> priv des <PASSWORD>

! SHA_AES
snmp-server user <USERNAME> network-admin auth sha <PASSWORD> priv aes-128 <PASSWORD>
```

Verify the result before running NaC:

```
show snmp user <USERNAME>
```

The `Auth` and `Priv` columns must match the row for your selected value in the table above.

> [!IMPORTANT]
> The authentication and privacy passphrases must be **identical**. NaC sends a single
> password (`NDFC_SW_PASSWORD`) to ND, which uses it for both. Mismatched passphrases are
> the most common cause of `notManageable` and SNMPv3 timeouts during discovery.

> [!NOTE]
> Always specify the privacy keyword explicitly. Omitting it (`priv <PASSWORD>`) relies on a
> platform default that is not guaranteed to be stable across NX-OS releases. `des` also
> emits a deprecation warning on current releases.

### 2. Environment variables

ND uses `NDFC_SW_USERNAME` and `NDFC_SW_PASSWORD` to reach the switch during discovery.
These values must match `<USERNAME>` and `<PASSWORD>` used in the NX-OS configuration above.

```bash
export NDFC_SW_USERNAME='<USERNAME>'
export NDFC_SW_PASSWORD='<PASSWORD>'
```

In `group_vars`, the standard lookup pattern is:

```yaml
# group_vars/nd/connection.yaml
ndfc_switch_username: "{{ lookup('env', 'NDFC_SW_USERNAME') }}"
ndfc_switch_password: "{{ lookup('env', 'NDFC_SW_PASSWORD') }}"
```

## End-to-End SHA_AES Example

### Step 1 — Configure NX-OS on each switch

```
username nac_discovery password <DISCOVERY_PASSWORD> role network-admin
snmp-server user nac_discovery network-admin auth sha <DISCOVERY_PASSWORD> priv aes-128 <DISCOVERY_PASSWORD>
```

Confirm the switch applied the expected algorithms:

```
show snmp user nac_discovery
```

Expect `Auth: sha` and `Priv: aes-128`.

### Step 2 — Set environment variables

```bash
export NDFC_SW_USERNAME='nac_discovery'
export NDFC_SW_PASSWORD='<DISCOVERY_PASSWORD>'
```

### Step 3 — Set auth_proto in the data model

```yaml title="global.nac.yaml"
---
vxlan:
  fabric:
    name: myfabric
    type: VXLAN_EVPN
  global:
    ibgp:
      auth_proto: SHA_AES
      bgp_asn: "65001"
      route_reflectors: 2
      anycast_gateway_mac: 20:20:00:00:00:aa
```

### Step 4 — Run NaC

```bash
ansible-playbook vxlan.yaml -i inventory.yaml --limit myfabric --forks 1
```

## Troubleshooting

If discovery fails with `notManageable` or an SNMPv3 timeout:

1. Confirm the authentication and privacy passphrases are identical on the switch.
2. Confirm the algorithms actually applied: `show snmp user <USERNAME>`.
3. Confirm `NDFC_SW_USERNAME` and `NDFC_SW_PASSWORD` are exported in the shell running the
   playbook, and that they match the NX-OS user.

ND receives the selection as an integer in the `snmpV3AuthProtocol` field of the
`test-reachability` payload. Use this mapping when inspecting API traffic:

| `auth_proto` | `snmpV3AuthProtocol` |
|---|---|
| `MD5` | `0` |
| `SHA` | `1` |
| `MD5_DES` | `2` |
| `MD5_AES` | `3` |
| `SHA_DES` | `4` |
| `SHA_AES` | `5` |

## Limitations

- `auth_proto` applies to **every switch in the fabric**; it cannot be set per switch.
- NX-OS supports `sha-256` authentication, but no `auth_proto` value selects it. Only the
  six values listed above are available.
- DES is a weak algorithm and NX-OS emits a deprecation warning when it is configured.
  Prefer `SHA_AES` for new deployments.

> [!NOTE]
> The `snmp-server user` commands in this guide were verified on NX-OS 10.5(5): each one
> produces the `Auth`/`Priv` combination listed in the table. On the ND side, `SHA_AES`
> discovery has been confirmed against ND 4.2; the other values are carried by the data
> model and the module mapping but have not been individually validated against ND.

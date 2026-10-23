# Copyright (c) 2025 Cisco Systems, Inc. and its affiliates
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import socket
import time

from ansible.module_utils.common.text.converters import to_text
from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail
from ansible.module_utils.urls import open_url
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError

from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.ndfc_executor import (
    NdfcModuleExecutor,
)
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.nd_smu import (
    parse_smu_versions,
)
from ansible_collections.cisco.nac_dc_vxlan.plugins.filter.version_compare import (
    version_compare,
)


class ActionModule(ActionBase):
    TRANSFERS_FILES = False
    _supports_check_mode = True

    # SMU history endpoint is only queried on this exact NDFC build (matches the
    # original role gate: ndfc_version | version_compare('12.6.0.267', '==')).
    SMU_ND_VERSION = "12.6.0.267"

    def run(self, tmp=None, task_vars=None):
        results = super(ActionModule, self).run(tmp, task_vars)
        task_vars = task_vars or {}
        results["changed"] = False

        conn = self._connection_params(task_vars)
        self._wait_for_nd(conn)
        self._verify_authorization(conn)
        nd_version = self._get_nd_version(conn)

        executor = NdfcModuleExecutor(self, task_vars, tmp)
        ndfc_version = self._get_ndfc_version(executor)
        nd_smu_versions = self._get_smu_versions(executor, ndfc_version)

        results["ansible_facts"] = {
            "nd_version": nd_version,
            "ndfc_version": ndfc_version,
            "nd_smu_versions": nd_smu_versions,
        }
        return results

    def _template(self, value):
        # group_vars/connection values reach action plugins as raw, untemplated
        # strings; render them before use (see resolve_files_root for the same).
        if isinstance(value, str) and "{{" in value:
            return self._templar.template(value, fail_on_undefined=False)
        return value

    def _as_text(self, value):
        value = self._template(value)
        if value is None:
            return None
        return to_text(value, errors="surrogate_or_strict")

    def _connection_params(self, task_vars):
        host = self._as_text(task_vars.get("ansible_host"))
        port = self._template(task_vars.get("ansible_httpapi_port")) or 443
        domain = self._as_text(task_vars.get("ansible_httpapi_login_domain")) or "local"
        user = self._as_text(task_vars.get("ansible_user"))
        password = self._as_text(task_vars.get("ansible_password"))
        if not host or not user or password in (None, ""):
            raise AnsibleActionFail(
                "connectivity_check requires ansible_host, ansible_user and ansible_password"
            )

        # IPv6 hosts arrive bracketed (e.g. [2001:db8::30]); brackets are valid
        # in a URL authority but must be stripped for a raw socket connection.
        bare_host = str(host).replace("[", "").replace("]", "")
        return {
            "host": host,
            "bare_host": bare_host,
            "port": int(port),
            "domain": domain,
            "user": user,
            "password": password,
            "base_url": "https://{0}:{1}".format(host, int(port)),
        }

    def _wait_for_nd(self, conn, timeout=30, interval=5, connect_timeout=5):
        deadline = time.time() + timeout
        last_err = None
        while time.time() < deadline:
            try:
                with socket.create_connection(
                    (conn["bare_host"], conn["port"]), timeout=connect_timeout
                ):
                    return
            except OSError as error:
                last_err = error
                time.sleep(interval)
        raise AnsibleActionFail(
            "Timed out waiting to connect to Nexus Dashboard at {0}. Check the "
            "Nexus Dashboard is reachable from the Ansible Controller. ({1})".format(
                conn["base_url"], last_err
            )
        )

    def _verify_authorization(self, conn, retries=5, delay=2):
        body = json.dumps(
            {
                "domain": conn["domain"],
                "userName": conn["user"],
                "userPasswd": conn["password"],
            }
        ).encode("utf-8")
        last = None
        for _attempt in range(retries):
            try:
                response = open_url(
                    conn["base_url"] + "/login",
                    method="POST",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    validate_certs=False,
                    timeout=30,
                )
                if response.getcode() == 200:
                    return
                last = response.getcode()
            except HTTPError as error:
                last = error.code
            except (URLError, OSError) as error:
                last = getattr(error, "reason", error)
            time.sleep(delay)
        raise AnsibleActionFail(
            "Nexus Dashboard authorization failed using specified ansible_user and "
            "ansible_password for {0}. Check Nexus Dashboard credentials and/or "
            "login domain.".format(conn["base_url"])
        )

    def _get_nd_version(self, conn):
        try:
            response = open_url(
                conn["base_url"] + "/version.json",
                method="GET",
                validate_certs=False,
                timeout=30,
            )
            if response.getcode() != 200:
                raise AnsibleActionFail(
                    "Expected HTTP 200 from {0}/version.json, got {1}".format(
                        conn["base_url"], response.getcode()
                    )
                )
            data = json.loads(response.read())
        except (HTTPError, URLError, OSError, ValueError) as error:
            raise AnsibleActionFail(
                "Failed to get Nexus Dashboard version from {0}/version.json: {1}".format(
                    conn["base_url"], error
                )
            )
        return "{0}.{1}.{2}{3}".format(
            data.get("major"),
            data.get("minor"),
            data.get("maintenance"),
            data.get("patch"),
        )

    def _get_ndfc_version(self, executor):
        result = executor.execute_rest(
            "GET", "/appcenter/cisco/ndfc/api/about/version"
        )
        try:
            return result["response"]["DATA"]["version"]
        except (KeyError, TypeError):
            raise AnsibleActionFail(
                "Could not determine NDFC version from /about/version response: "
                "{0}".format(result)
            )

    def _get_smu_versions(self, executor, ndfc_version):
        if not version_compare(ndfc_version, self.SMU_ND_VERSION, "=="):
            return []
        response = executor.execute_rest(
            "GET", "/api/v1/infra/systemSoftware/firmwares"
        )
        try:
            return parse_smu_versions(response)
        except ValueError as error:
            raise AnsibleActionFail(str(error))

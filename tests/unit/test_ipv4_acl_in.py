# Copyright (c) 2026 Cisco Systems, Inc. and its affiliates
# SPDX-License-Identifier: MIT

"""Exercise network ACL rendering, selective updates, and module dispatch offline.

Only controller-dependent preparation and the final DCNM action are replaced.
Templates, defaults, structural diffs, registries, and argument dispatch are real.
"""

import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.task import Task
from ansible.template import Templar

from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.build_resource_data import ResourceDataBuilder
from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.build_resource_data import ActionModule as BuildAction
from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.diff_compare import ActionModule as DiffAction
from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.manage_resources import ResourceManager
from ansible_collections.cisco.nac_dc_vxlan.plugins.action.dtc.remove_resources import ResourceRemover
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.ndfc_executor import NdfcModuleExecutor
from ansible_collections.cisco.nac_dc_vxlan.plugins.plugin_utils.pipeline_base import display


COLLECTION_ROOT = Path(__file__).resolve().parents[2]
FABRICS = ("VXLAN_EVPN", "eBGP_VXLAN", "MSD", "MCFG")
SMU_VERSION = "4.3.1.0175006011"
MISSING = object()


class CaptureAction:
    """Run local diff actions and capture final module arguments without a controller."""

    def __init__(self):
        self.calls = []
        self._task = Task()
        self.original_args = {"original": True}
        self._task.args = self.original_args
        self._task.action = "original_action"
        self._connection = SimpleNamespace(_shell=SimpleNamespace(tmpdir="unused"))
        self._play_context = None
        self._loader = DataLoader()
        self._templar = Templar(loader=self._loader)
        self._shared_loader_obj = SimpleNamespace(action_loader=SimpleNamespace(get=self.get_action))

    def get_action(self, module_name, **kwargs):
        if module_name == "cisco.nac_dc_vxlan.dtc.diff_compare":
            return DiffAction(**kwargs)
        if module_name == "cisco.nac_dc_vxlan.dtc.build_resource_data":
            return BuildAction(**kwargs)
        if module_name not in ("cisco.dcnm.dcnm_network", "cisco.dcnm.dcnm_vrf"):
            raise AssertionError("Unexpected action invocation: %s" % module_name)
        action = self

        class CapturedModuleAction:
            def run(self, task_vars=None, tmp=None):
                action.calls.append((module_name, copy.deepcopy(kwargs["task"].args)))
                return {"changed": False, "failed": False}

        return CapturedModuleAction()

    def _execute_module(self, module_name, module_args, **kwargs):
        self.calls.append((module_name, copy.deepcopy(module_args)))
        return {"changed": False, "failed": False}


@pytest.fixture(autouse=True)
def quiet_pipeline():
    with patch.object(display, "display"):
        yield


def model_for(fabric_type, networks):
    vxlan = {
        "fabric": {"name": "acl-test", "type": fabric_type},
        "topology": {"switches": [{"hostname": "leaf1"}]},
        "underlay": {"general": {"replication_mode": "ingress_replication"}},
    }
    overlay = {"networks": networks}
    if fabric_type in ("MSD", "MCFG"):
        vxlan["multisite"] = {"overlay": overlay}
    else:
        vxlan["overlay"] = overlay
    return {"vxlan": vxlan}


def network_defaults(defaults, fabric_type):
    vxlan = defaults["vxlan"]
    overlay = vxlan["multisite"]["overlay"] if fabric_type in ("MSD", "MCFG") else vxlan["overlay"]
    return overlay["networks"]


@pytest.fixture
def build_networks(tmp_path):
    role_path = tmp_path / "common"
    role_path.mkdir()
    (role_path / "templates").symlink_to(COLLECTION_ROOT / "roles/dtc/common/templates", target_is_directory=True)
    factory_defaults = yaml.safe_load((COLLECTION_ROOT / "roles/validate/files/defaults.yml").read_text())["factory_defaults"]

    def build(fabric_type, acl=MISSING, default_acl=MISSING, discovery=None,
              force=False, children=False, phase="networks"):
        net = {"name": "network1", "net_id": 30001, "vrf_name": "tenant1", "vlan_id": 101}
        if acl is not MISSING:
            net["ipv4_acl_in"] = acl
        if children:
            net["child_fabrics"] = [{"name": "child1"}]
        defaults = copy.deepcopy(factory_defaults)
        if default_acl is not MISSING:
            network_defaults(defaults, fabric_type)["ipv4_acl_in"] = default_acl
        data_model = model_for(fabric_type, [net])
        runtime_data = {
            "overlay_attach_groups": {"networks": [], "network_attach_groups_dict": {}},
            "child_fabrics_data": {"child1": {"attributes": {"REPLICATION_MODE": "ingress_replication"}}},
        }
        task_vars = {
            "data_model_extended": data_model,
            "defaults": defaults,
            "omit": "__omit_place_holder__unit_test",
            "nd_version": "4.4.1",
            "nd_smu_versions": [],
            "ndfc_version": "12.6.0.267",
            "runtime_msd_data_model": runtime_data,
            "runtime_mcfg_data_model": runtime_data,
            "common_role_path": str(role_path),
            "check_roles": {"save_previous": True},
        }
        for name, value in (discovery or {}).items():
            if value is MISSING:
                task_vars.pop(name, None)
            else:
                task_vars[name] = value
        params = {
            "fabric_type": fabric_type,
            "fabric_name": "acl-test",
            "data_model": data_model,
            "role_path": str(role_path),
            "run_map_diff_run": True,
            "force_run_all": force,
            "check_roles": {"save_previous": True},
        }
        if phase == "networks":
            params["resource_filter"] = ["networks"]
        action = CaptureAction()
        builder = ResourceDataBuilder(params, action, task_vars)
        if phase == "common":
            # Skip other resource builds; retain the real parent overlay
            # sentinel that gates deferred rendering in the create role.
            builder.resource_types = {}
        elif phase == "full":
            builder.resource_types = {"networks": builder.resource_types["networks"]}
        result = builder.build()
        assert not result["failed"], result
        return builder, result, action, task_vars

    return build


def run_create(result, action, task_vars, force=False, deferred=False):
    model = task_vars["data_model_extended"]
    fabric = model["vxlan"]["fabric"]
    params = {
        "fabric_type": fabric["type"], "fabric_name": fabric["name"], "data_model": model,
        "resource_data": result["resource_data"], "change_flags": result["change_flags"],
        "run_map_diff_run": True, "force_run_all": force,
    }
    task_vars["ansible_run_tags"] = ["cr_manage_networks"]
    runner = ResourceManager(params, NdfcModuleExecutor(action, task_vars), task_vars)
    # Controller preparation is replaced; selected tests retain the real
    # deferred parent render so forced runs exercise its full dispatch path.
    original_dispatch = runner._dispatch_internal_method

    def dispatch(resource_name, module, step):
        if deferred and module == "_msite_build_overlay":
            return original_dispatch(resource_name, module, step)
        return {"status": "ok", "changed": False}

    with patch.object(runner, "_dispatch_internal_method", side_effect=dispatch):
        outcome = runner.run_pipeline()
    assert not outcome["failed"], outcome
    assert action._task.args is action.original_args
    assert action._task.action == "original_action"
    return action.calls


@pytest.mark.parametrize("fabric_type", FABRICS)
@pytest.mark.parametrize("acl", ["TENANT-1-IN", "true", "123", 'acl: # "quoted" \\ name'])
def test_acl_string_survives_real_render_and_module_dispatch(build_networks, fabric_type, acl):
    _, result, action, task_vars = build_networks(fabric_type, acl=acl)
    calls = run_create(result, action, task_vars)
    assert len(calls) == 1
    module, args = calls[0]
    assert module == "cisco.dcnm.dcnm_network"
    assert args["state"] == "replaced"
    assert args["patch_version"] == "4.4.1"
    assert args["config"][0]["ipv4_acl_in"] == acl
    assert isinstance(args["config"][0]["ipv4_acl_in"], str)
    assert "patch_version" not in args["config"][0]


@pytest.mark.parametrize("fabric_type", FABRICS)
def test_optional_acl_and_custom_default_precedence(build_networks, fabric_type):
    _, absent, action, task_vars = build_networks(fabric_type)
    assert "ipv4_acl_in" not in run_create(absent, action, task_vars)[0][1]["config"][0]
    _, inherited, action, task_vars = build_networks(fabric_type, default_acl="DEFAULT-IN")
    assert run_create(inherited, action, task_vars)[0][1]["config"][0]["ipv4_acl_in"] == "DEFAULT-IN"
    _, explicit, action, task_vars = build_networks(fabric_type, acl="NETWORK-IN", default_acl="DEFAULT-IN")
    assert run_create(explicit, action, task_vars)[0][1]["config"][0]["ipv4_acl_in"] == "NETWORK-IN"


@pytest.mark.parametrize("fabric_type", FABRICS)
@pytest.mark.parametrize("acl", [None, ""])
def test_explicit_invalid_acl_does_not_inherit_default(build_networks, fabric_type, acl):
    # Schema validation rejects these network values. Rendering must preserve
    # their types instead of hiding an invalid request with a default value.
    _, result, _, _ = build_networks(fabric_type, acl=acl, default_acl="DEFAULT-IN")
    assert result["resource_data"]["networks"]["data"][0]["ipv4_acl_in"] == acl


@pytest.mark.parametrize("fabric_type", FABRICS)
def test_acl_add_update_remove_and_repeat_use_selective_diff(build_networks, fabric_type):
    build_networks(fabric_type)
    for acl in ("FIRST-IN", "SECOND-IN", MISSING):
        _, changed, action, task_vars = build_networks(fabric_type, acl=acl)
        assert changed["change_flags"]["changes_detected_networks"]
        assert changed["change_flags"]["changes_detected_any"]
        diff = changed["resource_data"]["networks"]["diff"]
        assert len(diff["updated"]) == 1
        assert diff["removed"] == []  # Removing the ACL updates, rather than deletes, the network.
        config = run_create(changed, action, task_vars)[0][1]["config"][0]
        if acl is MISSING:
            assert "ipv4_acl_in" not in config
        else:
            assert config["ipv4_acl_in"] == acl

        _, repeat, action, task_vars = build_networks(fabric_type, acl=acl)
        assert not repeat["change_flags"].get("changes_detected_networks", False)
        assert not repeat["change_flags"]["changes_detected_any"]
        assert repeat["resource_data"]["networks"]["diff"]["updated"] == []
        assert run_create(repeat, action, task_vars) == []


@pytest.mark.parametrize("fabric_type", ["MSD", "MCFG"])
def test_parent_acl_is_not_a_child_override(build_networks, fabric_type):
    _, result, action, task_vars = build_networks(fabric_type, acl="PARENT-IN", children=True)
    config = run_create(result, action, task_vars)[0][1]["config"][0]
    assert config["ipv4_acl_in"] == "PARENT-IN"
    assert all("ipv4_acl_in" not in child for child in config["child_fabric_config"])


@pytest.mark.parametrize("fabric_type", ["MSD", "MCFG"])
def test_parent_inherited_default_changes_reach_deferred_network_diff(build_networks, fabric_type):
    build_networks(fabric_type, phase="common")
    build_networks(fabric_type)
    for default_acl in ("FIRST-DEFAULT", "SECOND-DEFAULT", MISSING):
        _, common, _, _ = build_networks(fabric_type, default_acl=default_acl, phase="common")
        assert common["change_flags"]["changes_detected_networks"]
        assert common["change_flags"]["changes_detected_any"]
        _, deferred, action, task_vars = build_networks(fabric_type, default_acl=default_acl)
        assert len(deferred["resource_data"]["networks"]["diff"]["updated"]) == 1
        config = run_create(deferred, action, task_vars)[0][1]["config"][0]
        if default_acl is MISSING:
            assert "ipv4_acl_in" not in config
        else:
            assert config["ipv4_acl_in"] == default_acl

        _, common_repeat, _, _ = build_networks(fabric_type, default_acl=default_acl, phase="common")
        assert not common_repeat["change_flags"]["changes_detected_any"]
        _, deferred_repeat, _, _ = build_networks(fabric_type, default_acl=default_acl)
        assert deferred_repeat["resource_data"]["networks"]["diff"]["updated"] == []


@pytest.mark.parametrize("fabric_type", ["MSD", "MCFG"])
def test_parent_explicit_acls_ignore_irrelevant_default_change(build_networks, fabric_type):
    build_networks(fabric_type, acl="EXPLICIT-IN", phase="common")
    build_networks(fabric_type, acl="EXPLICIT-IN")
    _, common, _, _ = build_networks(fabric_type, acl="EXPLICIT-IN", default_acl="UNUSED-IN", phase="common")
    assert not common["change_flags"]["changes_detected_any"]
    _, deferred, _, _ = build_networks(fabric_type, acl="EXPLICIT-IN", default_acl="UNUSED-IN")
    assert deferred["resource_data"]["networks"]["diff"]["updated"] == []


@pytest.mark.parametrize("fabric_type", ["MSD", "MCFG"])
@pytest.mark.parametrize("networks", [[], None])
def test_parent_default_with_empty_networks_does_not_mutate_model(build_networks, fabric_type, networks):
    builder, _, _, _ = build_networks(fabric_type, default_acl="INHERITED-IN", phase="common")
    overlay = builder.data_model["vxlan"]["multisite"]["overlay"]
    assert "_ipv4_acl_in_default" not in overlay
    overlay["networks"] = networks
    original_overlay = copy.deepcopy(overlay)
    builder.change_flags = {}
    result = builder.build()
    assert not result["failed"], result
    assert overlay == original_overlay


@pytest.mark.parametrize("fabric_type", FABRICS)
def test_detected_version_only_changes_require_full_run(build_networks, fabric_type):
    _, initial, action, task_vars = build_networks(
        fabric_type, acl="TENANT-IN", discovery={"nd_version": "4.3.1", "nd_smu_versions": [SMU_VERSION]},
        force=True, phase="full",
    )
    assert run_create(initial, action, task_vars, force=True, deferred=True)[0][1]["patch_version"] == SMU_VERSION
    transitions = [
        ({"nd_version": "4.4.1", "nd_smu_versions": []}, "4.4.1"),
        ({"nd_version": "4.5.1", "nd_smu_versions": []}, "4.5.1"),
    ]
    for discovery, expected in transitions:
        phase = "common" if fabric_type in ("MSD", "MCFG") else "networks"
        _, repeat, action, task_vars = build_networks(fabric_type, acl="TENANT-IN", discovery=discovery, phase=phase)
        assert not repeat["change_flags"]["changes_detected_any"]
        assert run_create(repeat, action, task_vars, deferred=True) == []
        _, full, action, task_vars = build_networks(
            fabric_type, acl="TENANT-IN", discovery=discovery, force=True, phase="full",
        )
        assert full["change_flags"]["changes_detected_networks"]
        calls = run_create(full, action, task_vars, force=True, deferred=True)
        assert len(calls) == 1
        assert calls[0][1]["patch_version"] == expected
        assert calls[0][1]["config"][0]["ipv4_acl_in"] == "TENANT-IN"


@pytest.mark.parametrize("fabric_type", FABRICS)
@pytest.mark.parametrize("discovery,expected", [
    ({"nd_version": "4.3.1", "nd_smu_versions": ["4.3.1.99", SMU_VERSION, "4.3.1.10"]}, SMU_VERSION),
    ({"nd_version": "4.3.1", "nd_smu_versions": [SMU_VERSION]}, SMU_VERSION),
    ({"nd_version": "4.4.1a"}, "4.4.1"),
    ({"nd_version": "4.5.2.10", "nd_smu_versions": ["4.3.1.99"]}, "4.5.2"),
    ({"nd_version": "4.3.1", "nd_smu_versions": ["4.3.1.0175006012"]}, "4.3.1"),
    ({"nd_version": "4.4.1", "nd_version_response": {"json": {"major": 4, "minor": 5, "maintenance": 2}}}, "4.5.2"),
    ({"nd_version": MISSING, "nd_smu_versions": MISSING, "ndfc_version": "99.9.9"}, None),
    ({"nd_version": "malformed", "nd_smu_versions": [], "ndfc_version": "12.6.0.267"}, None),
])
def test_detected_version_reaches_each_network_pipeline(build_networks, fabric_type, discovery, expected):
    _, result, action, task_vars = build_networks(fabric_type, discovery=discovery)
    args = run_create(result, action, task_vars)[0][1]
    if expected is None:
        assert "patch_version" not in args
    else:
        assert args["patch_version"] == expected
    assert "patch_version" not in args["config"][0]


@pytest.mark.parametrize("fabric_type", FABRICS)
def test_inventory_override_cannot_enable_unsupported_detected_release(build_networks, fabric_type):
    _, result, action, task_vars = build_networks(
        fabric_type, discovery={"nd_version": "4.3.1", "patch_version": SMU_VERSION},
    )
    assert run_create(result, action, task_vars)[0][1]["patch_version"] == "4.3.1"


@pytest.mark.parametrize("module,state", [
    ("cisco.dcnm.dcnm_network", "deleted"),
    ("cisco.dcnm.dcnm_network", "query"),
    ("cisco.dcnm.dcnm_vrf", "replaced"),
    ("cisco.dcnm.dcnm_policy", "merged"),
])
def test_network_version_does_not_reach_other_modules_or_states(module, state):
    action = CaptureAction()
    NdfcModuleExecutor(action, {}).execute(
        module, state, [{"net_name": "network1"}], "acl-test", patch_version=SMU_VERSION,
    )
    assert "patch_version" not in action.calls[0][1]


@pytest.mark.parametrize("fabric_type", FABRICS)
def test_real_remove_pipeline_omits_detected_version(build_networks, fabric_type):
    _, result, action, task_vars = build_networks(fabric_type, discovery={"nd_smu_versions": [SMU_VERSION]})
    data = result["resource_data"]["networks"]["data"]
    result["resource_data"]["networks"]["diff"]["removed"] = data
    task_vars.update({
        "ansible_run_tags": ["rr_manage_networks"],
        "network_delete_mode": True, "multisite_network_delete_mode": True,
    })
    params = {
        "fabric_type": fabric_type, "fabric_name": "acl-test",
        "data_model": task_vars["data_model_extended"], "resource_data": result["resource_data"],
        "change_flags": result["change_flags"], "run_map_diff_run": True, "force_run_all": False,
    }
    runner = ResourceRemover(params, NdfcModuleExecutor(action, task_vars), task_vars)
    with patch.object(runner, "_pre_pipeline_setup", return_value={}), \
            patch.object(runner, "_is_active_child_fabric", return_value=False), \
            patch.object(runner, "_dispatch_internal_method", return_value={"status": "ok", "changed": False}):
        outcome = runner.run_pipeline()
    assert not outcome["failed"], outcome
    assert len(action.calls) == 1
    assert action.calls[0][1]["state"] == "deleted"
    assert "patch_version" not in action.calls[0][1]


def load_rule(fabric_type):
    relative_path = "multisite/204_overlay_networks.py" if fabric_type in ("MSD", "MCFG") else "common_vxlan/403_overlay_networks.py"
    path = COLLECTION_ROOT / "roles/validate/files/rules" / relative_path
    spec = importlib.util.spec_from_file_location("network_rule_" + fabric_type, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Rule


@pytest.mark.parametrize("fabric_type", FABRICS)
@pytest.mark.parametrize("value", [MISSING, "A", "A" * 64])
def test_custom_acl_default_valid_boundaries(fabric_type, value):
    model = model_for(fabric_type, [{"name": "network1"}])
    model["defaults"] = {"vxlan": {"overlay": {"networks": {}}, "multisite": {"overlay": {"networks": {}}}}}
    if value is not MISSING:
        network_defaults(model["defaults"], fabric_type)["ipv4_acl_in"] = value
    assert load_rule(fabric_type).match(model) == []


@pytest.mark.parametrize("fabric_type", FABRICS)
@pytest.mark.parametrize("value", ["", "A" * 65, None, 123, True, [], {}])
def test_custom_acl_default_invalid_values_are_rejected(fabric_type, value):
    model = model_for(fabric_type, [{"name": "network1"}])
    model["defaults"] = {"vxlan": {"overlay": {"networks": {}}, "multisite": {"overlay": {"networks": {}}}}}
    network_defaults(model["defaults"], fabric_type)["ipv4_acl_in"] = value
    messages = load_rule(fabric_type).match(model)
    assert len(messages) == 1
    assert "ipv4_acl_in" in messages[0]
    assert "1 to 64 characters" in messages[0]

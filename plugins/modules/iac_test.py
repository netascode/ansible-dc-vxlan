from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {"metadata_version": "0.1", "status": ["preview"]}

import os

from ansible.module_utils.basic import AnsibleModule

import iac_test.robot_writer
import iac_test.pabot

import sys
from io import StringIO


def run_module():
    module_args = dict(
        data=dict(type="list", required=True),
        templates=dict(type="str", required=True),
        filters=dict(type="str", default="", required=False),
        tests=dict(type="str", default="", required=False),
        output=dict(type="str", required=True),
        include=dict(type="list", default=[], required=False),
        exclude=dict(type="list", default=[], required=False),
        render_only=dict(type="bool", default=False, required=False),
        dry_run=dict(type="bool", default=False, required=False)
    )

    result = dict(changed=False)

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    # import epdb; epdb.set_trace()

    data = module.params["data"]
    templates = module.params["templates"]
    filters = module.params["filters"]
    tests = module.params["tests"]
    output = module.params["output"]
    include = module.params["include"]
    exclude = module.params["exclude"]
    render_only = module.params["render_only"]
    dry_run = module.params["dry_run"]

    paths = data
    paths.append(templates)
    if filters:
        paths.append(filters)
    if tests:
        paths.append(tests)

    for path in paths:
        if not os.path.exists(path):
            module.fail_json(msg=f"The provided directory {path} does not appear to exist!")

    for path in paths:
        if not os.listdir(path):
            module.fail_json(msg=f"The provided directory {path} exists but appears to be empty!")

    #### Option #1 ####
    #### iac-test class object & methods ####

    # writer = iac_test.robot_writer.RobotWriter(data, filters, tests, include, exclude)
    # writer.write(templates, output)
    # if not render_only:
    #     iac_test.pabot.run_pabot(outpiac_testut, include, exclude, dry_run)

    #### Option #2 ####
    #### iac-test cmd line wrapper ####

    options = []

    for item in data:
        options.append("--data")
        options.append(item)
    options.append("--templates")
    options.append(templates)
    if filters:
        options.append("--filters")
        options.append(filters)
    if tests:
        options.append("--tests")
        options.append(tests)
    options.append("--output")
    options.append(output)
    if include:
        for item in include:
            options.append("--include")
            options.append(item)
    if exclude:
        for item in exclude:
            options.append("--exclude")
            options.append(item)
    if render_only:
        options.append("--render-only")
    if dry_run:
        options.append("--dry-run")

    command = ["iac-test"]
    command.extend(options)
    result["command"] = command

    rc, _, _ = module.run_command(command)

    if rc > 0 and rc < 251:
        result["failed_tests"] = rc

    result["rc"] = rc
    result["changed"] = True

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()

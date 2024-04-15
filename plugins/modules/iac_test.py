from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {"metadata_version": "0.1", "status": ["preview"]}

import os

from ansible.module_utils.basic import AnsibleModule

import iac_test.robot_writer
import iac_test.pabot


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

    if output and not os.path.exists(output):
        module.fail_json(
            msg=f"The provided directory {output} does not appear to exist. Is it a directory?"
        )

    # writer = iac_test.robot_writer.RobotWriter(data, filters, tests, include, exclude)
    # writer.write(templates, output)
    # # iac_test.pabot.run_pabot(output, include, exclude, dry_run)
    # if not render_only:
    #     iac_test.pabot.run_pabot(output, include, exclude, dry_run)

    options = []

    if data:
        options.append("--data")
        options.append(data[0])
    if templates:
        options.append("--templates")
        options.append(templates)
    if output:
        options.append("--output")
        options.append(output)

    command = ["iac-test"]
    command.extend(options)

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

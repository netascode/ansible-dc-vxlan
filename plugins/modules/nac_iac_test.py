from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {"metadata_version": "0.1", "status": ["preview"]}

import os

from ansible.module_utils.basic import AnsibleModule


def run_module():
    module_args = dict(
        data_dir=dict(type="str", required=False),
        template_dir=dict(type="str", required=False),
        output_dir=dict(type="str", required=False),
    )

    result = dict(changed=False)

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    data_dir = module.params["data_dir"]
    template_dir = module.params["template_dir"]
    output_dir = module.params["output_dir"]

    if output_dir and not os.path.exists(output_dir):
        module.fail_json(
            msg="The provided directory (results_dir) does not appear to exist. Is it a directory?"
        )

    options = []

    if data_dir:
        options.append("--data")
        options.append(data_dir)
    if template_dir:
        options.append("--templates")
        options.append(template_dir)
    if output_dir:
        options.append("--output")
        options.append(output_dir)

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

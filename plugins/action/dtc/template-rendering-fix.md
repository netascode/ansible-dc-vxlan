# Fix: `ansible.builtin.template` "missing interpreter line" Error

## Error

```
fatal: [nac-ibgp-fabric1 -> localhost]: FAILED! => {
    "changed": false,
    "msg": "Unexpected error during resource build: AnsibleError: module (ansible.builtin.template) is missing interpreter line"
}
```

## Root Cause

The `_render_template()` method in `build_resource_data.py` was calling:

```python
self.action_module._execute_module(
    module_name='ansible.builtin.template',
    module_args={
        'src': template_src,
        'dest': output_path,
        'mode': '0644',
    },
    task_vars=self.task_vars,
    tmp=self.tmp,
)
```

`ansible.builtin.template` is an **action plugin**, not a standard Ansible module. The `_execute_module()` method expects a regular module — a Python script with a shebang line (`#!/usr/bin/python`) that gets transferred to the target host and executed. The `template` plugin has no such script; all of its logic runs on the controller side in the action plugin layer. When Ansible can't find a module file with an interpreter line, it raises this error.

## Fix

Replaced the `_execute_module()` call with direct Jinja2 rendering using Ansible's `Templar` class. This is the correct approach for rendering templates from within an action plugin.

### Changes

**File:** `plugins/action/dtc/build_resource_data.py`

1. **Added import** for `Templar`:

   ```python
   from ansible.template import Templar
   ```

2. **Replaced `_render_template()` implementation** — instead of delegating to the template module, the method now:
   - Reads the raw Jinja2 template file from disk
   - Creates an Ansible `Templar` instance with the action module's loader and the full `task_vars` context (preserving access to all variables, filters, and lookups)
   - Renders the template directly
   - Writes the output to disk and sets `0644` permissions

   ```python
   def _render_template(self, template_name, output_path):
       os.makedirs(os.path.dirname(output_path), exist_ok=True)

       template_src = self._find_template(template_name)

       # Determine which templates directory contains this template
       templates_dir = os.path.join(self.role_path, 'templates')
       if not template_src.startswith(templates_dir):
           templates_dir = os.path.join(self.collection_path, 'templates')

       with open(template_src, 'r') as f:
           template_content = f.read()

       # Set search path so {% include %} resolves correctly
       loader = self.action_module._loader
       original_basedir = loader.get_basedir()
       loader.set_basedir(templates_dir)

       try:
           templar = Templar(loader=loader, variables=self.task_vars)
           rendered = templar.template(template_content)
       except Exception as e:
           raise RuntimeError(
               f"Template rendering failed for '{template_name}': {str(e)}"
           )
       finally:
           loader.set_basedir(original_basedir)

       with open(output_path, 'w') as f:
           f.write(rendered)
       os.chmod(output_path, 0o644)
   ```

### Follow-up Fix: Jinja2 Include Search Path

The initial `Templar` fix resolved the interpreter line error but introduced a second issue:
templates using `{% include '/ndfc_fabric/dc_vxlan_fabric/dc_vxlan_fabric_base.j2' %}` couldn't
resolve the included template paths because the loader's `basedir` wasn't set to the role's
`templates/` directory.

**Error:**
```
"msg": "Resource build failed: Template rendering failed for 'ndfc_fabric.j2':
'/ndfc_fabric/dc_vxlan_fabric/dc_vxlan_fabric_base.j2' not found in search path: ..."
```

**Fix:** Before rendering, set the loader's `basedir` to the `templates/` directory of the role
(or collection) where the template was found, then restore it afterward. This mirrors what
Ansible's built-in template action plugin does internally.

## Why This Works

- `Templar` is Ansible's internal Jinja2 rendering engine — the same engine that the `template` action plugin uses under the hood.
- By passing `self.action_module._loader` and `self.task_vars`, the rendered templates have access to the same context (variables, filters, lookups) as they would in a standard `ansible.builtin.template` task.
- Since this action plugin runs entirely on the controller (localhost), there is no need to transfer a module script to a remote host — direct rendering is both correct and more efficient.

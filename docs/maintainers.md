# Maintainers Guide

Guidelines for the core maintainers of the VXLAN as Code Ansible Collection - above and beyond the [general developer guidelines](../CONTRIBUTING.md).

## Release Process Checklist

### Pre-Merge to `main` branch:

When we are considering publishing a new release, all of the following steps must be carried out (using the latest code base in `develop`):

1. Run full fabric profile integration regression tests against `develop`
     * Fix all bugs

1. Update [galaxy.yml](https://github.com/netascode/ansible-dc-vxlan/blob/develop/galaxy.yml) file
    * Update Version
        ```diff
        -  "version": "1.0.0",
        +  "version": "1.0.1",
        ```
    * Update authors as required
    * Update dependencies as required

1. Update [changelog.](https://github.com/netascode/ansible-dc-vxlan/blob/develop/CHANGELOG.rst)
     * Make sure CHANGELOG.md accurately reflects all changes since the last release
        * Apply a search filter: `is:issue closed:>=2025-03-01`
     * Add any significant changes that weren't documented in the changelog
     * Clean up any entries that are overly verbose, unclear, or otherwise could be improved
     * Indicate new support (if any)
     * Create release tag
       ```diff
       ...
       +.. _0.4.1: https://github.com/netascode/ansible-dc-vxlan/compare/0.4.0...0.4.1
        .. _0.4.0: https://github.com/netascode/ansible-dc-vxlan/compare/0.3.0...0.4.0
       ```

1. Scrub README docs
     * Update README docs for new support and where applicable

1. Pull release branch based on the `develop` branch
      * 0.0.x - a bugfix release
      * 0.x.0 - new feature(s)
      * x.0.0 - backward-incompatible change (if unvoidable!)

1. Open pull request from release branch against the `main` branch.
     * Ensure all GitHub Actions tasks have passed
     * Merge after approval

### Post-Merge to `main` branch:

1. Create annotated git tag for the release
     * [HowTo](https://git-scm.com/book/en/v2/Git-Basics-Tagging#Annotated-Tags)
  
1. Draft a [new release](https://github.com/netascode/ansible-dc-vxlan/releases) on GitHub
  
1. Merge `main` branch back into `develop` branch
     * Resolve any merge conflicts
     * Optional: Delete release branch (May want to keep for reference)

### Publish Release to Ansible Galaxy:

1. Publish to Ansible Galaxy

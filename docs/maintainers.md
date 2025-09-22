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
        -  "version": "0.4.0-dev",
        +  "version": "0.4.1-dev",
        ```
    * Update authors as required
    * Update dependencies as required

1. Update [changelog.](https://github.com/netascode/ansible-dc-vxlan/blob/develop/CHANGELOG.rst)
     * Make sure CHANGELOG.md accurately reflects all changes since the last release
        * Check all issues closed with search filter: `is:issue closed:>=2025-03-01`
        * Check all PRs merged with search filter: `is:pr merged:>=2025-03-01`
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

1. Commit doc changes for galaxy.yml, CHANGELOG.rst, and README.md to develop

1. Create a release branch based on the `develop` branch
      * 0.0.x - a bugfix release
      * 0.x.0 - new feature(s)
      * x.0.0 - backward-incompatible change (if unvoidable!)

1. On the release branch, edit galaxy.yml and remove the "-dev" from the version
      * version: 0.4.1    (instead of version: 0.4.1-dev)

1. Open pull request from release branch against the `main` branch
     * Ensure all GitHub Actions tasks have passed
     * Merge `release branch` into `main` after approval as `merge commit`

### Post-Merge to `main` branch:

1. git clone the repo in a new directory and create annotated git tag for the release
     * [HowTo](https://git-scm.com/book/en/v2/Git-Basics-Tagging#Annotated-Tags)
     * git clone ....
     * git switch main
     * git tag -a 0.4.1 -m "Release 0.4.1"
     * git show 0.4.1

1. Draft a [new release](https://github.com/netascode/ansible-dc-vxlan/releases) on GitHub

1. (Investigating. Merge `main` branch back into `develop` branch safely)

### Publish Release to Ansible Galaxy:

1. Publish to Ansible Galaxy

# Copyright (c) 2026 Cisco Systems, Inc. and its affiliates
# SPDX-License-Identifier: MIT

"""Allow these offline tests to run with pytest or ansible-test."""

import atexit
from pathlib import Path
from tempfile import TemporaryDirectory

from ansible.utils.collection_loader import AnsibleCollectionConfig
from ansible.utils.collection_loader._collection_finder import _AnsibleCollectionFinder


# ansible-test supplies the collection namespace. Standalone pytest also needs
# that namespace for the collection's imports and Ansible's Jinja filters.
if AnsibleCollectionConfig.collection_finder is None:
    collection_tree = TemporaryDirectory(prefix="nac-unit-collections-")
    atexit.register(collection_tree.cleanup)
    cisco_path = Path(collection_tree.name) / "ansible_collections" / "cisco"
    cisco_path.mkdir(parents=True)
    (cisco_path / "nac_dc_vxlan").symlink_to(Path(__file__).resolve().parents[2], target_is_directory=True)
    _AnsibleCollectionFinder(paths=[collection_tree.name])._install()

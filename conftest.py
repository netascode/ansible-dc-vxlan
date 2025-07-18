"""
Pytest configuration and fixtures for nac_dc_vxlan collection tests.
"""
import os
import sys

# Add the collections directory to Python path so ansible_collections.cisco.nac_dc_vxlan imports work
collections_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if collections_path not in sys.path:
    sys.path.insert(0, collections_path)

# Add the collection path to Python path
collection_path = os.path.abspath(os.path.dirname(__file__))
if collection_path not in sys.path:
    sys.path.insert(0, collection_path)

# Add the plugins path specifically
plugins_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'plugins'))
if plugins_path not in sys.path:
    sys.path.insert(0, plugins_path)

import pytest

# Configure pytest - this must be at top level
pytest_plugins = []

"""
Pytest configuration and fixtures for DTC action plugin tests.
"""
import os
import sys

# Add the collection path to Python path
collection_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
if collection_path not in sys.path:
    sys.path.insert(0, collection_path)

# Add the plugins path specifically
plugins_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'plugins'))
if plugins_path not in sys.path:
    sys.path.insert(0, plugins_path)

# Add the top-level collections path
top_collections_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..'))
if top_collections_path not in sys.path:
    sys.path.insert(0, top_collections_path)

import pytest

# Configure pytest
pytest_plugins = []

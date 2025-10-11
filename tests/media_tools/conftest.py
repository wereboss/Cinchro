# tests/media_tools/conftest.py

import pytest
import os
import json
from unittest.mock import MagicMock
from pathlib import Path
import sys
import httpx # Required by FastAPI TestClient

# Ensure local imports work by adjusting sys.path 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


@pytest.fixture(scope="session", autouse=True)
def setup_path():
    """Ensures the project root is on sys.path for absolute imports during testing."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

@pytest.fixture
def media_config_files(tmp_path) -> Path:
    """
    Creates temporary config.json and .env files for the Media Tools service
    in a unique directory and returns the path to that directory.
    """
    # Define the mock monitored paths
    MONITORED_PATHS = [
        "/mnt/media/Movies",
        "/mnt/media/Shows",
        "/mnt/archive/Old_Content"
    ]

    # 1. Create dummy config.json
    config_data = {
        "monitored_paths": MONITORED_PATHS,
        "api_host": "127.0.0.1",
        "api_port": 5000
    }
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(config_data, f)
        
    # 2. Create dummy .env file (empty for this service)
    env_path = tmp_path / ".env"
    with open(env_path, "w") as f:
        f.write("# Environment file for testing.")

    # Returns the path where the mock config files live
    return tmp_path


@pytest.fixture
def api_client(monkeypatch, media_config_files):
    """
    Creates a FastAPI TestClient, overriding the ConfigManager path to use the
    temporary media_config_files directory.
    """
    # 1. Import modules we need to patch/access
    from media_tools import api as media_api
    from media_tools import config as media_config
    from fastapi.testclient import TestClient

    # Store the original ConfigManager class
    OriginalConfigManager = media_config.ConfigManager

    # Define a temporary class that inherits from the original,
    # but forces the __init__ method to use our temporary paths.
    class MockedConfigManager(OriginalConfigManager):
        def __init__(self, **kwargs):
            temp_config_path = media_config_files / "config.json"
            temp_env_path = media_config_files / ".env"
            
            # Call the *parent's* constructor with the correct arguments
            super().__init__(
                config_path=str(temp_config_path), 
                env_path=str(temp_env_path)
            )

    # 2. Patch the module to use our MockedConfigManager
    monkeypatch.setattr(media_config, 'ConfigManager', MockedConfigManager)

    # 3. Re-instantiate the global config_manager object in the API module
    # This forces media_api.config_manager to use the patched class
    # and load the correct temporary configuration files.
    media_api.config_manager = MockedConfigManager()
    
    # 4. Create the client against the re-configured app
    return TestClient(media_api.app)

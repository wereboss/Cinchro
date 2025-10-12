# tests/ffmpeg_tools/conftest.py

import pytest
import os
import json
from pathlib import Path
import sys

# Ensure imports work by adding project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# --- Fixtures for Configuration ---

@pytest.fixture
def ffmpeg_config_files(tmp_path) -> Path:
    """
    Creates temporary config.json and .env files for the FFMPEG Tools service.
    """
    # 1. Configuration Data (config.json structure)
    config_data = {
      "api_host": "127.0.0.1",
      "api_port": 5001,
      "database_path": str(tmp_path / "ffmpeg_jobs.db"),
      # --- FIX: Changing mock paths to common Linux defaults ---
      "ffmpeg_path": "/usr/bin/ffmpeg", 
      "rsync_path": "/usr/bin/rsync",
      "media_machine_config": {
        "rsync_user": "test_user",
        "storage_host": "192.168.0.1",
        "archive_root_dir": "/mock/media/Archive"
      },
      "transfer_paths": {
        "local_temp_dir": str(tmp_path / "temp"),
        "local_output_dir": str(tmp_path / "output")
      }
    }

    # 2. Environment Variables (.env structure)
    # We explicitly define the SSH key path, though it's mocked here
    env_content = "SSH_KEY_PATH=/mock/keys/id_rsa_cinchro"

    # Write files to the temporary directory
    config_path = tmp_path / "config.json"
    env_path = tmp_path / ".env"
    
    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=2)
        
    with open(env_path, "w") as f:
        f.write(env_content)

    return tmp_path

# --- Fixture for Database Path ---

@pytest.fixture
def ffmpeg_db_path(ffmpeg_config_files) -> str:
    """
    Returns the temporary database path injected into the config.json fixture.
    """
    # We must read the injected path from the config file generated above
    config_path = ffmpeg_config_files / "config.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return config['database_path']
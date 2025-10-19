# tests/ffmpeg_tools/conftest.py (CORRECTED SCOPE)

import pytest
import os
import json
from pathlib import Path
import sys

# Ensure imports work by adding project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# --- Fixtures for Configuration ---

@pytest.fixture(scope="module") # FIX: Changing scope to module
def ffmpeg_config_files(tmp_path_factory) -> Path:
    """
    Creates temporary config.json and .env files for the FFMPEG Tools service
    in a module-level directory and returns the path to that directory.
    """
    # FIX: Using tmp_path_factory to create the directory manually
    tmp_path = tmp_path_factory.mktemp("ffmpeg_config")
    
    # 1. Configuration Data (config.json structure)
    config_data = {
      "api_host": "127.0.0.1",
      "api_port": 5001,
      "database_path": str(tmp_path / "ffmpeg_jobs.db"), # Inject temporary DB path here
      "ffmpeg_path": "/usr/bin/ffmpeg", # Corrected path for integration test
      "rsync_path": "/usr/bin/rsync",    # Corrected path for integration test
      "media_machine_config": {
        "rsync_user": "sayang",
        "storage_host": "192.168.0.112",
        "archive_root_dir": "/Users/sri/Movies/cinchro_tests/Archive"
      },
      "transfer_paths": {
        "local_temp_dir": "/home/sayang/Videos/Archive",
        "local_output_dir": "/home/sayang/Videos/cinchro"
      }
    }

    # 2. Environment Variables (.env structure)
    env_content = "SSH_KEY_PATH=/home/sayang/.ssh/macmini"

    # Write files to the temporary directory
    config_path = tmp_path / "config.json"
    env_path = tmp_path / ".env"
    
    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=2)
        
    with open(env_path, "w") as f:
        f.write(env_content)

    return tmp_path

# --- Fixture for Database Path ---
@pytest.fixture(scope="module") # FIX: Must match the scope of ffmpeg_config_files
def ffmpeg_db_path(ffmpeg_config_files) -> str:
    """
    Returns the temporary database path injected into the config.json fixture.
    """
    # We must read the injected path from the config file generated above
    config_path = ffmpeg_config_files / "config.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return config['database_path']
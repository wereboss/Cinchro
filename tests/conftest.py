# tests/conftest.py

import pytest
import os
import json
import sqlite3

@pytest.fixture(scope="function")
def test_config_files(tmp_path):
    """
    Fixture to create temporary config.json and .env files for a test.
    """
    orchestrator_dir = tmp_path / "orchestrator"
    orchestrator_dir.mkdir()
    
    config_path = orchestrator_dir / "config.json"
    env_path = orchestrator_dir / ".env"
    
    # Create a dummy config.json file
    config_data = {
        "LLM_MODEL": "test_model",
        "media_api_url": "http://test-media:5000",
        "ffmpeg_api_url": "http://test-ffmpeg:5001",
        "use_dummy_tools": True
    }
    with open(config_path, "w") as f:
        json.dump(config_data, f)
        
    # Create a dummy .env file
    env_content = f"DATABASE_PATH={orchestrator_dir / 'test.db'}\n"
    with open(env_path, "w") as f:
        f.write(env_content)
    
    # Yield the path to the temporary directory
    yield orchestrator_dir
    
    # Pytest's tmp_path fixture automatically handles cleanup.

@pytest.fixture(scope="function")
def test_db(tmp_path):
    """
    Fixture to create a temporary SQLite database file for a test.
    """
    db_path = tmp_path / "test.db"
    
    # Yield the database path to the test
    yield str(db_path)
    
    # Pytest's tmp_path fixture automatically handles cleanup.
# tests/ffmpeg_tools/test_api.py

import pytest
import os
import sys
import json
import time
from unittest.mock import MagicMock, patch
from datetime import datetime
from typing import Dict, Any

# Adjust path for internal imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import modules needed for testing
from ffmpeg_tools.api import app
from ffmpeg_tools.job_manager import JobManager
from ffmpeg_tools.database import JobDatabaseManager
from ffmpeg_tools.config import ConfigManager

# --- MOCK FIXTURES FOR API TESTING ---

@pytest.fixture
def mock_job_manager():
    """Mocks the JobManager instance."""
    manager = MagicMock(spec=JobManager)
    # Mock create_new_job to return a predictable ID immediately
    manager.create_new_job.return_value = "mock-job-1234"
    # Mock the internal methods if they were called (though the API should only call create_new_job)
    return manager

@pytest.fixture
def mock_db_manager():
    """Mocks the JobDatabaseManager instance."""
    db_manager = MagicMock(spec=JobDatabaseManager)
    
    # Define a default mock job entry for polling tests
    NOW_STR = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    
    db_manager.get_job.side_effect = lambda job_id: {
        # This mocks the COMPLETED job status after synchronous execution
        "mock-job-1234": {
            "job_id": "mock-job-1234",
            "status": "COMPLETED",
            "progress_percent": 100.0,
            "last_updated": NOW_STR,
            "notes": "All stages successful."
        },
        # This mocks a RUNNING job status for the status polling test
        "running-job-5678": {
            "job_id": "running-job-5678",
            "status": "PROCESSING",
            "progress_percent": 50.0,
            "last_updated": NOW_STR,
            "notes": "FFMPEG processing in progress."
        }
    }.get(job_id, {})
    
    return db_manager

@pytest.fixture
def ffmpeg_api_client(monkeypatch, mock_job_manager, mock_db_manager, ffmpeg_config_files):
    # 1. Patch the global instances in the API module
    # These assignments now work because the variables exist as globals in api.py
    monkeypatch.setattr(sys.modules['ffmpeg_tools.api'], 'job_manager', mock_job_manager)
    monkeypatch.setattr(sys.modules['ffmpeg_tools.api'], 'db_manager', mock_db_manager)
    from fastapi.testclient import TestClient

    # 2. Mock the ConfigManager instance creation itself to use our fixture files
    def mock_config_init(*args, **kwargs):
        return ConfigManager(
            config_path=str(ffmpeg_config_files / 'config.json'),
            env_path=str(ffmpeg_config_files / '.env')
        )
    
    monkeypatch.setattr(sys.modules['ffmpeg_tools.api'], 'config_manager', mock_config_init())
    
    # 3. Return the client
    return TestClient(app)

# --- TESTS ---

def test_status_endpoint_ok(ffmpeg_api_client):
    """Verifies the health check endpoint returns success."""
    response = ffmpeg_api_client.get("/status")
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "Cinchro FFMPEG Tools"

def test_submit_job_success(ffmpeg_api_client, mock_job_manager):
    """
    Tests job submission. Asserts the JobManager is called and the API returns 
    the final 'COMPLETED' status (due to synchronous execution mock).
    """
    # Test Payload
    payload = {
        "input_file": "/remote/media/Test_File_1080p.mkv", 
        "ffmpeg_command": "-c:v libx265 -crf 28"
    }
    
    response = ffmpeg_api_client.post("/submit-job", json=payload)
    response_data: Dict[str, Any] = response.json()
    
    # 1. Assert API Response (Assertions remain the same)
    assert response.status_code == 200
    assert response_data["status"] == "COMPLETED"
    assert response_data["job_id"] == "mock-job-1234"
    assert response_data["progress_percent"] == 100.0

    # 2. Assert JobManager was called correctly
    # FIX: Using POSITIONAL arguments to match the actual API call style.
    mock_job_manager.create_new_job.assert_called_once_with(
        payload['input_file'],   # positional argument 1
        payload['ffmpeg_command'] # positional argument 2
    )


def test_job_status_poll_completed(ffmpeg_api_client):
    """Tests the /job-status endpoint for a completed job."""
    job_id = "mock-job-1234"
    response = ffmpeg_api_client.get(f"/job-status/{job_id}")
    response_data: Dict[str, Any] = response.json()
    
    assert response.status_code == 200
    assert response_data["job_id"] == job_id
    assert response_data["status"] == "COMPLETED"
    assert response_data["current_stage"] == "COMPLETED"
    assert response_data["progress_percent"] == 100.0

def test_job_status_poll_running(ffmpeg_api_client):
    """Tests the /job-status endpoint for a job currently in progress."""
    job_id = "running-job-5678"
    response = ffmpeg_api_client.get(f"/job-status/{job_id}")
    response_data: Dict[str, Any] = response.json()
    
    assert response.status_code == 200
    assert response_data["status"] == "PROCESSING"
    assert response_data["progress_percent"] == 50.0

def test_job_status_not_found(ffmpeg_api_client):
    """Tests the /job-status endpoint returns 404 for an invalid ID."""
    response = ffmpeg_api_client.get("/job-status/invalid-uuid-000")
    assert response.status_code == 404
    assert "Job ID not found" in response.json()["detail"]
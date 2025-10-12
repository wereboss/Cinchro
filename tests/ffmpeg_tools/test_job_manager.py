# tests/ffmpeg_tools/test_job_manager.py

import pytest
import os
import subprocess
from unittest.mock import MagicMock, call
import time
from ffmpeg_tools.job_manager import JobManager
from ffmpeg_tools.config import ConfigManager
from ffmpeg_tools.database import JobDatabaseManager
from subprocess import CalledProcessError, CompletedProcess # Import specifically for mocks


# --- FIXTURES ---

@pytest.fixture
def mock_config(ffmpeg_config_files):
    """Provides a configured ConfigManager instance using temporary files."""
    # Instantiating ConfigManager directly with explicit paths
    return ConfigManager(
        config_path=str(ffmpeg_config_files / 'config.json'),
        env_path=str(ffmpeg_config_files / '.env')
    )

@pytest.fixture
def mock_manager(mock_config, ffmpeg_db_path):
    """Provides a JobManager instance initialized with necessary components."""
    db_manager = JobDatabaseManager(ffmpeg_db_path)
    return JobManager(mock_config, db_manager)

@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Fixture to mock subprocess.run for faking shell command execution."""
    
    # We define a mock function that always returns success unless instructed otherwise
    def mock_run(*args, **kwargs):
        # Return a mock CompletedProcess object indicating success
        return CompletedProcess(args[0], 0, stdout="Mock command output", stderr="")

    mock = MagicMock(side_effect=mock_run)
    monkeypatch.setattr(subprocess, 'run', mock)
    return mock

# --- TESTS ---

def test_01_job_creation_and_db_init(mock_manager, mock_config):
    """
    Verifies JobManager initializes and correctly sets up constants from config.
    """
    manager = mock_manager
    
    # 1. CRITICAL ASSERTION: Check that the config object itself has the correct value
    # If this fails, the issue is in ConfigManager's 'get' or JSON loading.
    assert mock_config.get("media_machine_config.rsync_user") == "test_user" 

    # 2. Assert JobManager received the correct values from the config instance
    assert manager.FFMPEG_PATH == "/usr/bin/ffmpeg"
    assert manager.RSYNC_USER == "test_user" # This is the value we expect it to pull
    assert manager.STORAGE_HOST == "192.168.0.1" # Example host
    
    assert os.path.exists(manager.LOCAL_TEMP_DIR)
    assert os.path.exists(manager.LOCAL_OUTPUT_DIR)

def test_02_rsync_command_structure(mock_manager):
    """Verifies the core rsync command structure is built correctly."""
    manager = mock_manager
    
    remote_src = "test_user@192.168.0.1:/remote/media/source.mkv"
    local_dest = "/mock/path/temp"
    
    expected_cmd_start = [
        "/usr/bin/rsync",  # Updated path
        "-az",
        "--partial",
        "--progress"
    ]
    
    actual_cmd = manager._build_rsync_cmd(remote_src, local_dest)
    
    # Assert only the first four elements which are the command and flags
    assert actual_cmd[:4] == expected_cmd_start
    # Assert the transfer destination is correct
    assert actual_cmd[-1] == local_dest
    
# --- Pipeline Tests ---

def test_03_full_pipeline_success_mocked(mock_manager, mock_subprocess_run, monkeypatch):
    """
    Tests a complete pipeline run where all subprocess calls succeed,
    verifying status updates are correctly persisted in the DB.
    """
    manager = mock_manager
    
    # Mock the time.sleep calls to speed up the simulated conversion loop
    mock_sleep = MagicMock()
    monkeypatch.setattr(time, 'sleep', mock_sleep)
    
    # 1. Create Job (This should also trigger run_job_pipeline)
    job_id = manager.create_new_job(
        input_file="/remote/media/file.mkv",
        ffmpeg_command="-c:v libx265 -crf 28"
    )

    # 2. Assert Subprocess calls were made for the 3 Rsync stages
    # Rsync uses the same mock for simplicity here. We verify its execution count.
    assert mock_subprocess_run.call_count >= 3  # PULL, BACKUP, PUSH

    # 3. Assert final status is COMPLETED
    final_job = manager.db.get_job(job_id)
    assert final_job['status'] == "COMPLETED"
    assert final_job['progress_percent'] == 100.0
    
    # 4. Assert local temp directory name was used in the transfer
    local_temp = manager.LOCAL_TEMP_DIR
    assert mock_subprocess_run.call_args_list[0].args[0][-1] == local_temp


def test_04_pipeline_fails_on_transfer(mock_manager, mock_subprocess_run):
    """
    Tests that the pipeline exits immediately when the PULL transfer fails (Stage 1).
    """
    manager = mock_manager
    
    # 1. Configure mock_subprocess_run to fail ONLY on the first call (PULL)
    def failing_rsync(*args, **kwargs):
        if mock_subprocess_run.call_count == 1:
            # Simulate rsync failure (Stage 1: TRANSFERRING_IN)
            raise CalledProcessError(1, args[0], stderr="Connection Refused")
        # All other calls (Stage 2, 3, 4) would theoretically succeed, but should not run
        return CompletedProcess(args[0], 0, stdout="Mock command output", stderr="")
    
    mock_subprocess_run.side_effect = failing_rsync

    # 2. Create Job (This triggers run_job_pipeline)
    job_id = manager.create_new_job(
        input_file="/remote/media/fail_file.mkv",
        ffmpeg_command="-c:v libx265 -crf 28"
    )

    # 3. Assert final status is FAILED and pipeline halted
    final_job = manager.db.get_job(job_id)
    
    assert final_job['status'] == "TRANSFERRING_IN_FAILED"
    assert "Connection Refused" in final_job['notes']
    
    # Since only the PULL stage ran, the subprocess count should be low (1 or 2 attempts)
    # Note: We can't strictly assert mock_subprocess_run.call_count due to internal retries,
    # but the status MUST reflect the first failure.
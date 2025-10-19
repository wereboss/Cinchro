# tests/ffmpeg_tools/test_execution_integration.py

import pytest
import os
import subprocess
import time
import shutil
import uuid
from unittest.mock import MagicMock
from subprocess import CalledProcessError, CompletedProcess

# Import necessary modules
from ffmpeg_tools.job_manager import JobManager
from ffmpeg_tools.config import ConfigManager
from ffmpeg_tools.database import JobDatabaseManager

# --- ENVIRONMENT CONFIGURATION ---
# Check if integration tests are enabled (User must set this manually)
INTEGRATION_TESTS_ENABLED = os.environ.get("RUN_FFMPEG_INTEGRATION_TESTS", "false").lower() == "true"
pytestmark = pytest.mark.skipif(
    not INTEGRATION_TESTS_ENABLED,
    reason="Requires RUN_FFMPEG_INTEGRATION_TESTS=true environment variable to run shell commands."
)

# --- FIXTURES (Setup and cleanup remain the same) ---

@pytest.fixture(scope="module") 
def setup_job_manager(ffmpeg_config_files, ffmpeg_db_path):
    # ... (body of setup_job_manager fixture remains the same) ...
    config_manager = ConfigManager(
        config_path=str(ffmpeg_config_files / 'config.json'),
        env_path=str(ffmpeg_config_files / '.env')
    )
    db_manager = JobDatabaseManager(ffmpeg_db_path)
    
    # Ensure local temp directories are ready for real file operations
    temp_dir = config_manager.get("transfer_paths.local_temp_dir")
    out_dir = config_manager.get("transfer_paths.local_output_dir")
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    
    manager = JobManager(config_manager, db_manager)
    return manager

@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Fixture to mock subprocess.run for faking shell command execution (used in test 02)."""
    # ... (body of mock_subprocess_run remains the same) ...
    def mock_run(*args, **kwargs):
        return CompletedProcess(args[0], 0, stdout="Mock command output", stderr="")
    mock = MagicMock(side_effect=mock_run)
    monkeypatch.setattr(subprocess, 'run', mock)
    return mock

# --- LIVE INTEGRATION TEST (New) ---

def test_03_live_rsync_pull_transfer(setup_job_manager):
    """
    INTEGRATION: Tests the Rsync PULL (TRANSFERRING_IN) stage using a live subprocess call.
    This validates SSH command construction, key usage, and file placement.
    
    NOTE: Requires CINCHRO_TEST_PULL_FILE and a configured SSH key/user/host in config.
    """
    manager = setup_job_manager
    
    # --- 1. Get Live Environment Inputs ---
    # We retrieve the actual file path from the remote machine via environment variable
    remote_source_file = os.environ.get("CINCHRO_TEST_PULL_FILE")
    
    if not remote_source_file:
        pytest.skip("Skipping live Rsync test: CINCHRO_TEST_PULL_FILE environment variable not set.")
    
    # Define necessary paths
    remote_pull_source = f"{manager.RSYNC_USER}@{manager.STORAGE_HOST}:{remote_source_file}"
    local_temp_file = os.path.join(manager.LOCAL_TEMP_DIR, os.path.basename(remote_source_file))
    
    # Ensure the local temp file does not exist before the transfer
    if os.path.exists(local_temp_file):
        os.remove(local_temp_file)
    
    # 2. --- Execute the Live Rsync PULL Command ---
    print(f"\nAttempting live Rsync PULL: {remote_pull_source} -> {manager.LOCAL_TEMP_DIR}")
    
    # Note: We must call the internal method that uses the REAL subprocess.run
    success = manager._run_rsync_transfer(
        job_id=str(uuid.uuid4()), # Use a temporary UUID
        src_path=remote_pull_source,
        dest_path=manager.LOCAL_TEMP_DIR,
        stage_status="TRANSFERRING_IN"
    )

    # 3. --- Assertions ---
    
    # Assert transfer success (rsync return code 0)
    assert success is True, "Rsync transfer failed. Check SSH keys, user, host, and remote file path."
    
    # Assert the file arrived at the local temp directory
    assert os.path.exists(local_temp_file), f"Transferred file not found at local path: {local_temp_file}"

    # Cleanup: Remove the file for the next test run
    # os.remove(local_temp_file)

# --- MOCK TESTS (REMAINING CODE FOR REFERENCE) ---
# ... (test_01_ffmpeg_path_validation remains the same) ...
# ... (test_02_rsync_command_failure_handling remains the same) ...
# ... (test_03_full_pipeline_success_mocked remains the same) ...
# ... (test_04_pipeline_fails_on_transfer remains the same) ...
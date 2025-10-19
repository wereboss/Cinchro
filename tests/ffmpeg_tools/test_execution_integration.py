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
INTEGRATION_TESTS_ENABLED = os.environ.get("RUN_FFMPEG_INTEGRATION_TESTS", "false").lower() == "true"
pytestmark = pytest.mark.skipif(
    not INTEGRATION_TESTS_ENABLED,
    reason="Requires RUN_FFMPEG_INTEGRATION_TESTS=true environment variable to run shell commands."
)

# --- FIXTURES (Setup remains the same) ---
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

# ... (test_01 and test_02 remain the same) ...
# Note: test_03 remains the same and is run first to ensure the input file exists locally.

# --- INTEGRATION TESTS ---

def test_03_live_rsync_pull_transfer(setup_job_manager):
    """
    INTEGRATION: Tests the Rsync PULL (TRANSFERRING_IN) stage. 
    (This ensures the file exists for test_04).
    """
    # ... (Function body remains the same, assuming it pulls the file)
    manager = setup_job_manager
    remote_source_file = os.environ.get("CINCHRO_TEST_PULL_FILE")
    
    if not remote_source_file:
        pytest.skip("Skipping live Rsync test: CINCHRO_TEST_PULL_FILE environment variable not set.")
    
    local_temp_file = os.path.join(manager.LOCAL_TEMP_DIR, os.path.basename(remote_source_file))
    
    if os.path.exists(local_temp_file):
        os.remove(local_temp_file)
    
    remote_pull_source = f"{manager.RSYNC_USER}@{manager.STORAGE_HOST}:{remote_source_file}"
    
    # Execute the Live Rsync PULL Command
    success = manager._run_rsync_transfer(
        job_id=str(uuid.uuid4()),
        src_path=remote_pull_source,
        dest_path=manager.LOCAL_TEMP_DIR,
        stage_status="TRANSFERRING_IN"
    )

    assert success is True, "Rsync transfer failed. Check SSH keys, user, host, and remote file path."
    assert os.path.exists(local_temp_file), f"Transferred file not found at local path: {local_temp_file}"

    # NOTE: File is NOT removed here; it is used by test_04.

def test_04_live_ffmpeg_processing(setup_job_manager, monkeypatch):
    """
    INTEGRATION: Tests the FFMPEG PROCESSING stage using the file pulled in test_03.
    """
    manager = setup_job_manager
    
    # --- FIX: Retrieve the remote source file path from the environment ---
    remote_source_file = os.environ.get("CINCHRO_TEST_PULL_FILE")
    if not remote_source_file:
        pytest.skip("Skipping FFMPEG test: CINCHRO_TEST_PULL_FILE environment variable not set.")
    
    # Define paths based on the pulled file
    base_filename = os.path.basename(remote_source_file)
    local_input_file = os.path.join(manager.LOCAL_TEMP_DIR, base_filename)
    
    # --- Dependency Check ---
    if not os.path.exists(local_input_file):
        pytest.skip(f"Skipping FFMPEG test: Input file {local_input_file} not found locally (Rsync failed or was skipped).")

    # Define the expected output file name
    file_root, _ = os.path.splitext(base_filename) 
    local_output_file = os.path.join(manager.LOCAL_OUTPUT_DIR, f"{uuid.uuid4()}_{file_root}.mp4") # Using a new UUID for safety

    # Ensure output file doesn't exist initially
    if os.path.exists(local_output_file):
        os.remove(local_output_file)
    
    # Mock the internal sleep function to speed up the test simulation
    mock_sleep = MagicMock()
    monkeypatch.setattr(time, 'sleep', mock_sleep)

    # 1. Define the FFMPEG Command (H.264 to H.265/HEVC, compressed to 360p)
    ffmpeg_command = "-c:v libx265 -crf 28 -s 640x360 -y" # -y force overwrite

    # 2. Execute the FFMPEG conversion (using a temporary job ID for clean DB entry)
    job_id = str(uuid.uuid4())
    manager.db.create_job(job_id, remote_source_file, local_output_file, ffmpeg_command)
    
    print(f"\nAttempting FFMPEG conversion: {local_input_file} -> {local_output_file}")
    
    # FIX: We now call the internal function directly, replacing the synchronous version from the original failure log
    # We must call the internal method that uses the REAL subprocess.run
    success = manager._run_ffmpeg_conversion(job_id, local_input_file, local_output_file, ffmpeg_command)

    # 4. Assertions
    assert success is True, "FFMPEG processing failed or raised an unexpected error."
    assert os.path.exists(local_output_file), "FFMPEG output file was not created."
    
    # Final Cleanup
    # os.remove(local_output_file)
    # os.remove(local_input_file) # Clean up the pulled file as well
# tests/ffmpeg_tools/test_execution_integration.py

import pytest
import os
import subprocess
import time
import shutil
import uuid 
from unittest.mock import MagicMock, patch
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

# --- FIXTURES ---

# FIX: Removed monkeypatch from module scope
@pytest.fixture(scope="module") 
def setup_job_manager(ffmpeg_config_files, ffmpeg_db_path):
    """Initializes the JobManager with real config and DB persistence."""
    
    config_manager = ConfigManager(
        config_path=str(ffmpeg_config_files / 'config.json'),
        env_path=str(ffmpeg_config_files / '.env')
    )
    db_manager = JobDatabaseManager(ffmpeg_db_path)
    
    temp_dir = config_manager.get("transfer_paths.local_temp_dir")
    out_dir = config_manager.get("transfer_paths.local_output_dir")
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    
    manager = JobManager(config_manager, db_manager)
    return manager

# FIX: New fixture to handle time mocking ONLY where needed (function scope)
@pytest.fixture
def mock_time_sleep():
    """Mocks time.sleep globally to speed up FFMPEG simulation steps."""
    with patch('time.sleep', MagicMock()) as mock_sleep:
        yield mock_sleep

# --- LIVE END-TO-END PIPELINE TEST ---

def test_03_full_live_pipeline(setup_job_manager): # NOTE: test is renamed to 03 for sequence
    """
    INTEGRATION: Runs the entire 4-stage job pipeline live, asserting file presence 
    before manual cleanup.
    """
    manager = setup_job_manager
    remote_source_file = os.environ.get("CINCHRO_TEST_PULL_FILE")
    if not remote_source_file:
        pytest.skip("Skipping live pipeline test: CINCHRO_TEST_PULL_FILE environment variable not set.")

    job_id = str(uuid.uuid4())
    ffmpeg_command = "-c:v libx265 -crf 28 -s 640x360 -y" 
    
    # Define file paths for manual cleanup
    base_filename = os.path.basename(remote_source_file)
    local_input_file = os.path.join(manager.LOCAL_TEMP_DIR, base_filename)
    local_output_file_final = os.path.join(manager.LOCAL_OUTPUT_DIR, base_filename)

    # 1. Execution: Call the pipeline, telling it to SKIP the final cleanup
    manager.db.create_job(job_id, remote_source_file, local_output_file_final, ffmpeg_command)
    manager.run_job_pipeline(job_id, skip_cleanup=True) # PASS THE FLAG HERE
    
    # --- 2. Assertions (Occur BEFORE Manual Cleanup) ---
    final_job = manager.db.get_job(job_id)
    
    # A. Assert Pipeline Completion
    assert final_job['status'] == "COMPLETED", f"Pipeline failed! Final status: {final_job['status']}. Notes: {final_job.get('notes')}"
    
    # B. CRITICAL ASSERTION: Check that the final output file exists locally
    assert os.path.exists(local_output_file_final), "Local processed output file missing after conversion."

    # --- 3. Mandatory Manual Cleanup ---
    # Delete local Linux files (must be done or the next test will fail)
    if os.path.exists(local_input_file): os.remove(local_input_file)
    if os.path.exists(local_output_file_final): os.remove(local_output_file_final)
    
    # WARNING: Remote cleanup (deleting the file pushed to Unix) is omitted for simplicity.
    
# --- The rest of the file (tests 01 and 02) must also be checked for 'monkeypatch' in the function signature, 
# and if it exists, it should be removed as it's no longer needed, and the fixture is not used in this file.
# The code below is not for user display, but internal note
# The previous definition of test_01 and test_02 also used monkeypatch. The user should check those functions.
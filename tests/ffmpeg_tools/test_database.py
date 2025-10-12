# tests/ffmpeg_tools/test_database.py

import pytest
from ffmpeg_tools.database import JobDatabaseManager
import os
import time

# Note: ffmpeg_db_path fixture is auto-discovered from conftest.py

@pytest.fixture
def db_manager(ffmpeg_db_path):
    """Provides a clean instance of JobDatabaseManager for each test."""
    # Ensure the database file is clean/removed before starting (though tmp_path should handle this)
    if os.path.exists(ffmpeg_db_path):
        os.remove(ffmpeg_db_path)
        
    manager = JobDatabaseManager(ffmpeg_db_path)
    yield manager
    manager.close()

def test_db_creation_and_check(db_manager, ffmpeg_db_path):
    """Verifies that the database file and table are created."""
    assert os.path.exists(ffmpeg_db_path)
    # Attempt to query a column to ensure the table structure is correct
    job = db_manager.get_job('non_existent_id')
    assert job == {}

def test_create_and_get_job(db_manager):
    """Tests creating a new job and retrieving its initial state."""
    job_id = "test-job-123"
    input_file = "/remote/media/input.mkv"
    output_file = "/local/output/output.mp4"
    command = "-c:v libx265 -crf 28"
    
    db_manager.create_job(job_id, input_file, output_file, command)
    
    job = db_manager.get_job(job_id)
    
    assert job['job_id'] == job_id
    assert job['status'] == 'SUBMITTED'
    assert job['input_file'] == input_file
    assert job['output_file'] == output_file
    assert job['ffmpeg_command'] == command
    assert job['progress_percent'] == 0.0

def test_update_job_status_and_progress(db_manager):
    """Tests updating multiple fields on an existing job."""
    job_id = "test-job-456"
    db_manager.create_job(job_id, "/in/f.mkv", "/out/f.mp4", "-c:v copy")
    
    # Simulate first stage update
    db_manager.update_job_status(job_id, "TRANSFERRING_IN", progress=15.5, notes="Transfer 15% complete.")
    job_1 = db_manager.get_job(job_id)
    
    assert job_1['status'] == 'TRANSFERRING_IN'
    assert job_1['progress_percent'] == 15.5
    assert "Transfer 15% complete." in job_1['notes']
    
    # Simulate final stage update
    db_manager.update_job_status(job_id, "COMPLETED", progress=100.0, notes="Job finished.")
    job_2 = db_manager.get_job(job_id)
    
    assert job_2['status'] == 'COMPLETED'
    assert job_2['progress_percent'] == 100.0
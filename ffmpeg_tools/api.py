# ffmpeg_tools/api.py

import os
import sys
import json
import logging
import uuid
import time
from datetime import datetime, timedelta # FIX: Added datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Union, Optional, List

# Ensure local imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ffmpeg_tools.config import ConfigManager
from ffmpeg_tools.database import JobDatabaseManager
from ffmpeg_tools.job_manager import JobManager

# Define global variables first (allows monkeypatch to set attributes)
config_manager = None
db_manager = None
job_manager = None

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Pydantic Schemas for API ---

class JobSubmissionDetails(BaseModel):
    """Schema for submitting an FFMPEG conversion job."""
    input_file: str
    ffmpeg_command: str

class JobStatusResponse(BaseModel):
    """Schema for returning detailed job status and progress."""
    job_id: str
    status: str
    current_stage: str
    progress_percent: float # Percentage completion of the CURRENT STAGE
    time_elapsed_seconds: Optional[int]
    notes: str
    
# --- Core Logic and Initialization ---
# Initialize the objects only once, lazily.
def initialize_dependencies():
    """Initializes global dependencies for the API service."""
    global config_manager, db_manager, job_manager
    if config_manager is None:
        config_manager = ConfigManager()
        db_manager = JobDatabaseManager(config_manager.get("database_path"))
        job_manager = JobManager(config_manager, db_manager)

# Execute initialization immediately so the endpoints can use the objects
initialize_dependencies()

# --- FastAPI Application ---
app = FastAPI(title="Cinchro FFMPEG Tools API", version="0.1.0")


@app.get("/status", response_model=Dict[str, str])
def get_service_status():
    """Returns the operational status of the FFMPEG Tools service."""
    return {"status": "ok", "service": "Cinchro FFMPEG Tools", "machine": "Linux"}


@app.post("/submit-job", response_model=JobStatusResponse)
def submit_ffmpeg_job(job_details: JobSubmissionDetails):
    """
    Receives a conversion job request and kicks off the multi-stage pipeline.
    Returns the initial job status.
    """
    logger.info(f"API received job request for: {job_details.input_file}")
    
    try:
        # Create and run the pipeline immediately (synchronous for MVP)
        job_id = job_manager.create_new_job(job_details.input_file, job_details.ffmpeg_command)
        
        # Retrieve the final status from the database after synchronous execution
        job_entry = db_manager.get_job(job_id)

        # We need a string parsing-safe timestamp for elapsed time calculation
        # The stored timestamp is a string, which we will use to calculate time elapsed
        
        # Since the job is already COMPLETED/FAILED here, we just need to return the final status
        time_elapsed = int(time.time() - time.mktime(datetime.strptime(job_entry['last_updated'], "%Y-%m-%dT%H:%M:%S.%f").timetuple()))
        
        # The status field holds the current stage name (e.g., COMPLETED)
        return JobStatusResponse(
            job_id=job_id,
            status=job_entry['status'],
            current_stage=job_entry['status'],
            progress_percent=job_entry['progress_percent'],
            time_elapsed_seconds=time_elapsed,
            notes=job_entry.get('notes', 'Job processing successful.')
        )

    except Exception as e:
        logger.error(f"Error submitting job: {e}")
        # Mark as FAILED in case of external exception
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {e}")


@app.get("/job-status/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    """
    Allows the orchestrator to poll for job status, progress, and current stage.
    """
    job_entry = db_manager.get_job(job_id)
    
    if not job_entry:
        raise HTTPException(status_code=404, detail="Job ID not found in database.")

    status = job_entry['status']
    
    # Calculate time elapsed based on the stored last_updated timestamp
    try:
        # NOTE: We use the creation time for total time, but last_updated for status.
        # Since the JobManager updates quickly, we just use current time difference for now.
        last_updated_ts = time.mktime(datetime.strptime(job_entry['last_updated'], "%Y-%m-%dT%H:%M:%S.%f").timetuple())
        time_elapsed = int(time.time() - last_updated_ts)
    except Exception:
        time_elapsed = 0 # Handle potential parsing error

    return JobStatusResponse(
        job_id=job_id,
        status=status,
        current_stage=status, # The status field directly reflects the current stage (TRANSFERRING_IN, PROCESSING, etc.)
        progress_percent=job_entry.get('progress_percent', 0.0),
        time_elapsed_seconds=time_elapsed,
        notes=job_entry.get('notes', 'Job status retrieved.')
    )
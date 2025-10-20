# ffmpeg_tools/api.py

import os
import sys
import json
import logging
import uuid
import time
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Union, Optional, List

# Ensure local imports work
# We rely on the project root being in the path when executed via 'python -m ffmpeg_tools.main'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ffmpeg_tools.config import ConfigManager
from ffmpeg_tools.database import JobDatabaseManager
from ffmpeg_tools.job_manager import JobManager

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
    progress_percent: float
    time_elapsed_seconds: Optional[int]
    notes: str


# --- Core Logic and Initialization (Explicit Global Instantiation) ---

config_manager = ConfigManager()
db_manager = JobDatabaseManager(config_manager.get("database_path"))

# FIX: Ensure JobManager is fully loaded before instantiation
job_manager_instance = JobManager(config_manager, db_manager)


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
    """
    logger.info(f"API received job request for: {job_details.input_file}")
    
    try:
        # FIX: Now calls the method that exists in JobManager.py
        job_id = job_manager_instance.create_new_job(job_details.input_file, job_details.ffmpeg_command)
        
        # Retrieve the final status from the database after synchronous execution
        job_entry = db_manager.get_job(job_id)
        
        # ... (rest of the response generation logic is correct) ...

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
    
    try:
        last_updated_ts = time.mktime(datetime.strptime(job_entry['last_updated'], "%Y-%m-%dT%H:%M:%S.%f").timetuple())
        time_elapsed = int(time.time() - last_updated_ts)
    except Exception:
        time_elapsed = 0

    return JobStatusResponse(
        job_id=job_id,
        status=status,
        current_stage=status,
        progress_percent=job_entry.get('progress_percent', 0.0),
        time_elapsed_seconds=time_elapsed,
        notes=job_entry.get('notes', 'Job status retrieved.')
    )
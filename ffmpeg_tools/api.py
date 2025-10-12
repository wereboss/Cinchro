# ffmpeg_tools/api.py

import os
import json
import logging
import subprocess
import uuid
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Union, Optional

# Import the local config manager
from .config import ConfigManager

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Global Job Storage (In-memory for MVP) ---
# { job_id: { status: str, progress: float, start_time: float, details: dict } }
JOB_STORAGE: Dict[str, Dict[str, Union[str, float, dict]]] = {} 

# --- Pydantic Schemas for API ---

class FFMPEGJob(BaseModel):
    """Schema for submitting an FFMPEG conversion job."""
    input_file: str
    output_file: str
    command: str

class JobStatus(BaseModel):
    """Schema for returning job status and progress."""
    job_id: str
    status: str
    progress_percent: float
    time_elapsed_seconds: Optional[int]
    estimated_time_remaining_seconds: Optional[int]
    notes: str


# --- Core Logic and Utilities ---
# Initialize Configuration
config_manager = ConfigManager()

# --- FFMPEG Execution Function (Synchronous for MVP) ---

def run_ffmpeg_job(job_id: str, input_file: str, output_file: str, command: str, ffmpeg_path: str):
    """
    Simulates executing an FFMPEG job and updates global job storage.
    NOTE: In a real environment, this would run asynchronously (subprocess.Popen)
          and use a complex parsing logic to stream progress updates. 
          For the MVP, we simulate a delay and update the status in stages.
    """
    global JOB_STORAGE
    
    full_command = f"{ffmpeg_path} -i {input_file} {command} {output_file}"
    
    logger.info(f"Starting job {job_id}: {full_command}")
    
    # --- STAGE 1: Submitted -> Running ---
    JOB_STORAGE[job_id]['status'] = 'RUNNING'
    JOB_STORAGE[job_id]['start_time'] = time.time()
    
    # Simulate time-consuming work (replace with actual subprocess.run in production)
    for i in range(1, 10):
        time.sleep(0.05) # Simulate workload
        JOB_STORAGE[job_id]['progress_percent'] = round(i * 10, 2)
        # Update notes with simulated progress
        JOB_STORAGE[job_id]['details']['notes'] = f"Progress: {JOB_STORAGE[job_id]['progress_percent']}%"
        logger.debug(f"Job {job_id} progress: {JOB_STORAGE[job_id]['progress_percent']}%")

    # --- STAGE 2: Finished ---
    JOB_STORAGE[job_id]['status'] = 'COMPLETED'
    JOB_STORAGE[job_id]['progress_percent'] = 100.0
    JOB_STORAGE[job_id]['details']['notes'] = "Conversion successful."
    
    logger.info(f"Job {job_id} completed successfully.")
    return True


# --- FastAPI Application ---

app = FastAPI(title="Cinchro FFMPEG Tools API", version="0.1.0")


@app.get("/status", response_model=Dict[str, str])
def get_service_status():
    """Returns the operational status of the FFMPEG Tools service."""
    return {"status": "ok", "service": "Cinchro FFMPEG Tools", "machine": "Linux"}


@app.post("/run-ffmpeg", response_model=JobStatus)
def run_ffmpeg_endpoint(job_details: FFMPEGJob):
    """
    Receives a conversion job, submits it to the execution queue, and returns the Job ID.
    """
    global JOB_STORAGE
    
    job_id = str(uuid.uuid4())
    ffmpeg_path = config_manager.get("ffmpeg_path", "ffmpeg") # Default to 'ffmpeg' if not in config
    
    # Create the initial job entry
    JOB_STORAGE[job_id] = {
        'status': 'SUBMITTED',
        'progress_percent': 0.0,
        'start_time': 0.0,
        'details': job_details.dict(),
    }
    
    # NOTE: Since this is an MVP, we are running the job synchronously (blocking the API call).
    # In a production environment, this should be dispatched to a background worker (e.g., Celery).
    
    try:
        run_ffmpeg_job(job_id, job_details.input_file, job_details.output_file, job_details.command, ffmpeg_path)
    except Exception as e:
        JOB_STORAGE[job_id]['status'] = 'FAILED'
        JOB_STORAGE[job_id]['details']['error'] = str(e)
        logger.error(f"Job {job_id} failed during execution: {e}")

    # Return the final status immediately after synchronous execution
    job_entry = JOB_STORAGE.get(job_id, {})
    return JobStatus(
        job_id=job_id,
        status=job_entry.get('status', 'FAILED'),
        progress_percent=job_entry.get('progress_percent', 0.0),
        time_elapsed_seconds=int(time.time() - job_entry.get('start_time', time.time())),
        estimated_time_remaining_seconds=0,
        notes=job_entry['details'].get('notes', job_entry['details'].get('error', 'Execution completed.'))
    )


@app.get("/job-status/{job_id}", response_model=JobStatus)
def get_job_status(job_id: str):
    """
    Allows the orchestrator to poll for job status, progress, and estimated time remaining.
    """
    job_entry = JOB_STORAGE.get(job_id)
    
    if not job_entry:
        raise HTTPException(status_code=404, detail="Job ID not found.")

    status = job_entry['status']
    progress = job_entry['progress_percent']
    
    time_elapsed = 0
    eta = None
    
    if job_entry.get('start_time'):
        time_elapsed = int(time.time() - job_entry['start_time'])
        
        if progress > 0 and status == 'RUNNING':
            # Simple ETA calculation: (Total time = Time elapsed / Progress) - Time elapsed
            estimated_total = time_elapsed / (progress / 100.0)
            eta = int(estimated_total - time_elapsed)

    return JobStatus(
        job_id=job_id,
        status=status,
        progress_percent=progress,
        time_elapsed_seconds=time_elapsed,
        estimated_time_remaining_seconds=eta,
        notes=job_entry['details'].get('notes', 'Job status retrieved.')
    )
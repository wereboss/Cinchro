# ffmpeg_tools/job_manager.py

import os
import sys
import uuid
import subprocess
import time
import json
from typing import Dict, Any, List

# Add path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from ffmpeg_tools.config import ConfigManager
from ffmpeg_tools.database import JobDatabaseManager


# --- Core FFMPEG Job Manager ---

class JobManager:
    """
    Manages the multi-stage conversion pipeline: PULL, BACKUP, PROCESS, PUSH.
    Uses subprocess/rsync for reliable, network-based file operations.
    """

    def __init__(self, config_manager: ConfigManager, db_manager: JobDatabaseManager):
        self.config = config_manager
        self.db = db_manager
        
        # --- Constants from Config ---
        self.FFMPEG_PATH = self.config.get("ffmpeg_path", "ffmpeg")
        self.RSYNC_PATH = self.config.get("rsync_path", "rsync")
        
        # --- SSH/Transfer Config ---
        self.RSYNC_USER = self.config.get("media_machine_config.rsync_user") 
        self.STORAGE_HOST = self.config.get("media_machine_config.storage_host")
        self.ARCHIVE_ROOT_DIR = self.config.get("media_machine_config.archive_root_dir")
        self.SSH_KEY_PATH = self.config.get("SSH_KEY_PATH") 
        
        # --- Local/Remote Paths ---
        self.LOCAL_TEMP_DIR = self.config.get("transfer_paths.local_temp_dir", "/tmp/cinchro_linux_jobs/temp")
        self.LOCAL_OUTPUT_DIR = self.config.get("transfer_paths.local_output_dir", "/tmp/cinchro_linux_jobs/output")

        # Ensure local directories exist
        os.makedirs(self.LOCAL_TEMP_DIR, exist_ok=True)
        os.makedirs(self.LOCAL_OUTPUT_DIR, exist_ok=True)

        # DEBUG CHECK
        print(f"DEBUG_CHECK: RSYNC_USER received: {self.RSYNC_USER}")
        print(f"JobManager initialized. Storage Host: {self.STORAGE_HOST}")

    def create_new_job(self, input_file: str, ffmpeg_command: str) -> str:
        """Generates a job ID and initializes the job in the local database."""
        job_id = str(uuid.uuid4())
        
        # --- PATH CONSTRUCTION LOGIC (The Fix) ---
        base_name = os.path.basename(input_file)
        
        # 1. Strip the original extension cleanly (e.g., Trials720.mp4 -> Trials720)
        file_root, original_ext = os.path.splitext(base_name)
        
        # 2. Add the target extension (.mp4, as assumed for output)
        local_output_filename = f"{job_id}_{file_root}.mp4"
        local_output_file = os.path.join(self.LOCAL_OUTPUT_DIR, local_output_filename)
        
        # DEBUG CHECK: Log the final determined paths
        print(f"DEBUG: Input Base: {base_name}, Output Final: {local_output_file}")
        # --- END PATH CONSTRUCTION LOGIC ---

        # Create initial DB record (Note: local_output_file is passed as output_file)
        self.db.create_job(job_id, input_file, local_output_file, ffmpeg_command)
        
        # Immediately kick off the pipeline (synchronously for this MVP)
        self.run_job_pipeline(job_id)
        
        return job_id

    def _build_rsync_cmd(self, src: str, dest: str) -> List[str]:
        """Constructs the base rsync command for either pull or push."""
        rsync_cmd = [
            self.RSYNC_PATH,
            "-az",  # Archive mode, compress
            "--partial",  # Allow resuming
            "--progress", # Show progress (for future parsing)
        ]
        if self.SSH_KEY_PATH:
            # Use -i to specify the identity file for SSH
            rsync_cmd.extend(["-e", f"ssh -i {self.SSH_KEY_PATH}"])
            
        rsync_cmd.extend([src, dest])
        return rsync_cmd

    def _run_rsync_transfer(self, job_id: str, src_path: str, dest_path: str, stage_status: str) -> bool:
        """Handles PULL (from remote) or PUSH (to remote) using rsync."""
        
        self.db.update_job_status(job_id, stage_status, notes=f"Starting {stage_status} transfer.")
        print(f"Job {job_id}: {stage_status} in progress. Destination: {dest_path}")

        try:
            rsync_cmd = self._build_rsync_cmd(src_path, dest_path)
            
            # Execute rsync (synchronous execution for this MVP)
            result = subprocess.run(
                rsync_cmd,
                capture_output=True, 
                text=True, 
                check=True # Raise CalledProcessError if rsync fails
            )
            
            print(f"Job {job_id} {stage_status} complete. Output:\n{result.stdout}")
            self.db.update_job_status(job_id, stage_status + "_COMPLETE", 
                                      notes=f"{stage_status} successful.")
            return True

        except subprocess.CalledProcessError as e:
            error_note = f"RSYNC {stage_status} FAILED. Command: {' '.join(rsync_cmd)}. Error: {e.stderr}"
            print(error_note)
            self.db.update_job_status(job_id, stage_status + "_FAILED", notes=error_note)
            return False
        except Exception as e:
            error_note = f"Transfer failed due to unexpected error: {e}"
            self.db.update_job_status(job_id, stage_status + "_FAILED", notes=error_note)
            return False

    def _run_ffmpeg_conversion(self, job_id: str, local_input: str, local_output: str, command: str) -> bool:
        """
        Executes the FFMPEG conversion process using subprocess.
        Note: The progress update logic (time.sleep loop) is removed for this test,
        as we are now executing the single, real command synchronously.
        """
        
        self.db.update_job_status(job_id, "PROCESSING", progress=0.0, notes="Starting FFMPEG conversion.")
        print(f"Job {job_id}: FFMPEG conversion started. Output target: {local_output}")

        # 1. Construct the FFMPEG Command
        # The command includes input, output, and parameters read from the job
        
        # We must carefully build the command list to avoid shell injection and parsing issues.
        # We assume command is a string like: "-c:v libx265 -crf 28 -s 640x360 -y"
        
        ffmpeg_cmd = [self.FFMPEG_PATH, '-i', local_input]
        ffmpeg_cmd.extend(command.split())
        ffmpeg_cmd.append(local_output)
        
        try:
            # 2. Execute the FFMPEG process LIVE
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=True # Will raise CalledProcessError on non-zero exit code
            )
            
            # The synchronous call is complete. Update DB.
            self.db.update_job_status(job_id, "PROCESSING_COMPLETE", progress=100.0, notes="FFMPEG finished successfully.")
            
            # Print FFMPEG output for debugging purposes
            print(f"FFMPEG STDOUT:\n{result.stdout}")
            print(f"FFMPEG STDERR (Errors/Warnings):\n{result.stderr}")
            
            # 3. Final verification that the file exists on disk
            if not os.path.exists(local_output):
                raise FileNotFoundError(f"FFMPEG reported success, but file was not found at {local_output}")

            return True

        except subprocess.CalledProcessError as e:
            error_note = f"FFMPEG EXECUTION FAILED. Command exited with code {e.returncode}. STDERR: {e.stderr}"
            print(error_note)
            self.db.update_job_status(job_id, "PROCESSING_FAILED", notes=error_note)
            return False
        except FileNotFoundError as e:
            error_note = f"FFMPEG failed to create output file: {e}"
            print(error_note)
            self.db.update_job_status(job_id, "PROCESSING_FAILED", notes=error_note)
            return False
        except Exception as e:
            error_note = f"Unexpected error during FFMPEG process: {e}"
            print(error_note)
            self.db.update_job_status(job_id, "PROCESSING_FAILED", notes=error_note)
            return False

    def run_job_pipeline(self, job_id: str):
        """Orchestrates the 4-stage job pipeline."""
        
        job_data = self.db.get_job(job_id)
        if not job_data:
            print(f"Error: Job {job_id} not found.")
            return

        # 1. --- Define Paths ---
        remote_source_file = job_data['input_file']
        local_output_file = job_data['output_file']
        
        # Local temp file path for the file while it's being worked on
        local_temp_file = os.path.join(self.LOCAL_TEMP_DIR, os.path.basename(remote_source_file))
        
        # Remote/Rsync Targets (USER@HOST:PATH)
        remote_pull_source = f"{self.RSYNC_USER}@{self.STORAGE_HOST}:{remote_source_file}"
        remote_archive_destination = f"{self.RSYNC_USER}@{self.STORAGE_HOST}:{self.ARCHIVE_ROOT_DIR}"
        remote_push_destination = f"{self.RSYNC_USER}@{self.STORAGE_HOST}:{os.path.dirname(remote_source_file)}"
        
        print(f"Job {job_id} starting pipeline. Source: {remote_source_file}")

        # --- STAGE 1: PULL (Transfer to Linux Temp) ---
        # Destination is the local temp directory
        if not self._run_rsync_transfer(job_id, remote_pull_source, self.LOCAL_TEMP_DIR, "TRANSFERRING_IN"):
            return # Exit pipeline on failure

        # --- STAGE 2: BACKUP (Transfer Original Source to Unix Archive) ---
        # Source is the remote file path; Destination is the remote archive path
        if not self._run_rsync_transfer(job_id, remote_pull_source, remote_archive_destination, "BACKUP_SOURCE"):
            return # Exit pipeline on failure

        # --- STAGE 3: PROCESS (FFMPEG Conversion) ---
        if not self._run_ffmpeg_conversion(job_id, local_temp_file, local_output_file, job_data['ffmpeg_command']):
            return # Exit pipeline on failure

        # --- STAGE 4: PUSH (Transfer Converted File to Unix Source Location) ---
        # Source is the local output file; Destination is the remote source folder
        if not self._run_rsync_transfer(job_id, local_output_file, remote_push_destination, "TRANSFERRING_OUT"):
            return # Exit pipeline on failure

        # --- STAGE 5: Cleanup and Finalization ---
        # In a real system, we'd delete local temp and output files here.
        self.db.update_job_status(job_id, "COMPLETED", notes="All stages successful.")
        print(f"Job {job_id} pipeline fully completed and archived.")
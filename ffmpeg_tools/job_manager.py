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
    # ... (rest of __init__ remains the same) ...
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
        self.SSH_KEY_PATH = self.config.get("SSH_KEY_PATH", os.getenv("SSH_KEY_PATH"))
        
        # --- Local/Remote Paths ---
        self.LOCAL_TEMP_DIR = self.config.get("transfer_paths.local_temp_dir", "/tmp/cinchro_linux_jobs/temp")
        self.LOCAL_OUTPUT_DIR = self.config.get("transfer_paths.local_output_dir", "/tmp/cinchro_linux_jobs/output")

        # Ensure local directories exist
        os.makedirs(self.LOCAL_TEMP_DIR, exist_ok=True)
        os.makedirs(self.LOCAL_OUTPUT_DIR, exist_ok=True)

        print(f"JobManager initialized. Storage Host: {self.STORAGE_HOST}")

    # ... (_build_rsync_cmd and _run_rsync_transfer methods remain the same) ...
    
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
            error_note = f"RSYNC {stage_status} FAILED. Command: {' '.join(e.cmd)}. Error: {e.stderr}"
            print(error_note)
            self.db.update_job_status(job_id, stage_status + "_FAILED", notes=error_note)
            return False
        except Exception as e:
            error_note = f"Transfer failed due to unexpected error: {e}"
            self.db.update_job_status(job_id, stage_status + "_FAILED", notes=error_note)
            return False

    def _run_remote_backup(self, job_id: str, remote_file: str) -> bool:
        """
        Executes a remote SSH command on the Unix machine to copy the source file
        to the archive path on the same machine.
        """
        self.db.update_job_status(job_id, "BACKUP_SOURCE", notes="Executing remote copy command.")
        print(f"Job {job_id}: BACKUP_SOURCE in progress. Source: {remote_file}")

        # Command: ssh user@host "cp source_file archive_dir/"
        remote_command = (
            f"cp -f '{remote_file}' '{self.ARCHIVE_ROOT_DIR}/'"
        )

        ssh_cmd = [
            'ssh', 
            '-i', self.SSH_KEY_PATH, 
            f"{self.RSYNC_USER}@{self.STORAGE_HOST}",
            remote_command
        ]

        try:
            # Execute SSH command (synchronous)
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.stderr:
                # Cp errors often appear on stderr even with check=True
                raise subprocess.CalledProcessError(1, ssh_cmd, stderr=result.stderr)

            print(f"Job {job_id} BACKUP_SOURCE complete. Output:\n{result.stdout}")
            self.db.update_job_status(job_id, "BACKUP_SOURCE_COMPLETE", progress=100.0, 
                                      notes="Remote backup successful (SSH cp).")
            return True

        except subprocess.CalledProcessError as e:
            error_note = f"REMOTE BACKUP FAILED (SSH). Command: {' '.join(e.cmd)}. Error: {e.stderr}"
            print(error_note)
            self.db.update_job_status(job_id, "BACKUP_SOURCE_FAILED", notes=error_note)
            return False
        except Exception as e:
            error_note = f"Remote backup failed due to unexpected error: {e}"
            self.db.update_job_status(job_id, "BACKUP_SOURCE_FAILED", notes=error_note)
            return False

    def _run_ffmpeg_conversion(self, job_id: str, local_input: str, local_output: str, command: str) -> bool:
    # ... (FFMPEG conversion logic remains the same) ...
        self.db.update_job_status(job_id, "PROCESSING", progress=0.0, notes="Starting FFMPEG conversion.")
        print(f"Job {job_id}: FFMPEG conversion started. Output target: {local_output}")

        ffmpeg_cmd = [self.FFMPEG_PATH, '-i', local_input]
        ffmpeg_cmd.extend(command.split())
        ffmpeg_cmd.append(local_output)
        
        try:
            # Execute the FFMPEG process LIVE
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            self.db.update_job_status(job_id, "PROCESSING_COMPLETE", progress=100.0, notes="FFMPEG finished successfully.")
            
            print(f"FFMPEG STDOUT:\n{result.stdout}")
            print(f"FFMPEG STDERR (Errors/Warnings):\n{result.stderr}")
            
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

    def _get_final_remote_path(self, job_id: str, remote_push_destination: str, local_output_file: str) -> str:
        """
        Calculates the final remote destination path, stripping the UUID prefix 
        from the local output file name.
        """
        local_base_name = os.path.basename(local_output_file)
        
        # Strip the UUID prefix (e.g., "6fbba10e-ff59-476e-806c-4e9f744230c8_")
        if local_base_name.startswith(f"{job_id}_"):
            final_name = local_base_name[len(job_id) + 1:]
        else:
            final_name = local_base_name
            
        # The rsync destination needs the user@host:path/filename format for the final target file
        remote_final_path = os.path.join(remote_push_destination, final_name)
        
        return remote_final_path

    def run_job_pipeline(self, job_id: str, skip_cleanup: bool = False): # ADDED skip_cleanup flag
        """Orchestrates the 4-stage job pipeline."""
        
        job_data = self.db.get_job(job_id)
        if not job_data:
            print(f"Error: Job {job_id} not found.")
            return

        # 1. --- Define Paths ---
        remote_source_file = job_data['input_file']
        base_filename = os.path.basename(remote_source_file)
        
        # Local paths
        local_temp_file = os.path.join(self.LOCAL_TEMP_DIR, base_filename)
        local_output_file_uuid = job_data['output_file'] # Original file with UUID prefix
        
        # Final desired local output path (without UUID)
        local_output_file_final = os.path.join(self.LOCAL_OUTPUT_DIR, base_filename)


        # Remote/Rsync Targets (USER@HOST:PATH)
        remote_pull_source = f"{self.RSYNC_USER}@{self.STORAGE_HOST}:{remote_source_file}"
        remote_push_destination_root = f"{self.RSYNC_USER}@{self.STORAGE_HOST}:{os.path.dirname(remote_source_file)}"
        
        print(f"Job {job_id} starting pipeline. Source: {remote_source_file}")

        # --- STAGE 1: PULL (Transfer to Linux Temp) ---
        if not self._run_rsync_transfer(job_id, remote_pull_source, self.LOCAL_TEMP_DIR, "TRANSFERRING_IN"):
            return 

        # --- STAGE 2: BACKUP (Remote SSH Copy on Unix Machine) ---
        if not self._run_remote_backup(job_id, remote_source_file):
            return 

        # --- STAGE 3: PROCESS (FFMPEG Conversion) ---
        # NOTE: FFMPEG OUTPUT still goes to the UUID file name initially
        if not self._run_ffmpeg_conversion(job_id, local_temp_file, local_output_file_uuid, job_data['ffmpeg_command']):
            return 

        # --- INTERMEDIATE STEP: Rename Local Output to Final Name (No UUID) ---
        if os.path.exists(local_output_file_uuid):
            os.rename(local_output_file_uuid, local_output_file_final)
            print(f"Job {job_id}: Renamed local output to final name: {local_output_file_final}")
        else:
            self.db.update_job_status(job_id, "PROCESSING_FAILED", notes="FFMPEG did not create output file for rename.")
            return

        # --- STAGE 4: PUSH (Transfer Renamed File back to Unix Source Location) ---
        # Source is now the file with the clean name. Destination is the directory root.
        if not self._run_rsync_transfer(job_id, local_output_file_final, remote_push_destination_root, "TRANSFERRING_OUT"):
            return 

        # --- STAGE 5: Cleanup and Finalization ---
        if not skip_cleanup: # Only run cleanup if the flag is False
            # Final cleanup: Remove local working files
            local_temp_file = os.path.join(self.LOCAL_TEMP_DIR, base_filename) # Need local paths again
            local_output_file_final = os.path.join(self.LOCAL_OUTPUT_DIR, base_filename)
            
            if os.path.exists(local_temp_file): os.remove(local_temp_file)
            if os.path.exists(local_output_file_final): os.remove(local_output_file_final)
            print("Cleanup complete.")
        else:
            print("Cleanup skipped for testing purposes.")


        self.db.update_job_status(job_id, "COMPLETED", notes="All stages successful.")
        print(f"Job {job_id} pipeline fully completed and archived.")
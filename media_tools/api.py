# media_tools/api.py

import os
import json
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

# Import the local config manager
from .config import ConfigManager

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Pydantic Schemas for API ---

class FilePath(BaseModel):
    """Schema for requesting metadata for a specific file."""
    file_path: str


# --- Core Logic and Utilities ---

# Initialize Configuration
config_manager = ConfigManager()

# A simple mock for metadata extraction (This is fine to remain as we don't have ffprobe installed)
def _get_mock_metadata(file_path: str) -> Dict[str, Any]:
    """
    Simulates calling ffprobe to get structured media metadata.
    This logic remains mock-based because we don't want a dependency on ffprobe
    for the basic API service to run.
    """
    # Look for patterns in the *real* file name provided by the orchestrator (e.g., test-1080p.mkv)
    if "1080p" in file_path and "hevc" in file_path.lower():
        return {
            "file_path": file_path,
            "video_codec": "HEVC",
            "resolution": "1920x1080",
            "audio_channels": 6,
            "bitrate_kbps": 5000
        }
    elif "2160p" in file_path:
        return {
            "file_path": file_path,
            "video_codec": "HEVC",
            "resolution": "3840x2160",
            "audio_channels": 8,
            "bitrate_kbps": 12000
        }
    else:
        # Default/unwanted file metadata
        return {
            "file_path": file_path,
            "video_codec": "AVC",
            "resolution": "1280x720",
            "audio_channels": 2,
            "bitrate_kbps": 2500
        }


# --- FastAPI Application ---

app = FastAPI(title="Cinchro Media Tools API", version="0.1.0")


@app.get("/status", response_model=Dict[str, str])
def get_service_status():
    """Returns the operational status of the Media Tools service."""
    return {"status": "ok", "service": "Cinchro Media Tools", "machine": "Unix"}


@app.get("/scan-files", response_model=List[str])
def scan_media_paths() -> List[str]:
    """
    Triggers a scan across all configured paths and returns a consolidated list
    of ACTUAL file paths found on the file system.
    """
    monitored_paths = config_manager.get("monitored_paths", [])
    found_files = []
    
    logger.info(f"Executing REAL file system scan for: {monitored_paths}")

    for path in monitored_paths:
        try:
            # Check if the path exists before attempting to list contents
            if not os.path.isdir(path):
                logger.warning(f"Monitored path does not exist: {path}")
                continue

            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                
                if os.path.isfile(full_path):
                    # Filter for common media extensions
                    if item.lower().endswith(('.mkv', '.mp4', '.mov')):
                        found_files.append(full_path)

        except PermissionError:
            logger.error(f"Permission denied accessing path: {path}")
        except Exception as e:
            logger.error(f"Error during scan of {path}: {e}")
    
    logger.info(f"Scan complete. Found {len(found_files)} files.")
    return found_files


@app.post("/get-metadata", response_model=Dict[str, Any])
def get_file_metadata_endpoint(file_info: FilePath) -> Dict[str, Any]:
    """
    Retrieves detailed metadata for a single file using a simulated ffprobe utility.
    """
    file_path = file_info.file_path
    
    metadata = _get_mock_metadata(file_path)
    
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Metadata not found for file: {file_path}")
    
    return metadata
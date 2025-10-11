# media_tools/api.py

import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

# Import the local config manager and ensure the path is correct for local imports
# In a true deployment, the system knows to look locally first.
from .config import ConfigManager


# --- Pydantic Schemas for API ---

class FilePath(BaseModel):
    """Schema for requesting metadata for a specific file."""
    file_path: str


# --- Core Logic and Utilities ---

# Initialize Configuration
# Assuming config.json and .env exist in the current directory
config_manager = ConfigManager()

# Mock function to simulate a call to ffprobe to get media metadata
def _simulate_ffprobe(file_path: str) -> Dict[str, Any]:
    """
    Simulates calling ffprobe to get structured media metadata.
    This logic mirrors the deterministic evaluation needed by the orchestrator.
    """
    # Define criteria for simulation
    if "1080p_hevc" in file_path:
        return {
            "file_path": file_path,
            "video_codec": "HEVC",
            "resolution": "1920x1080",
            "audio_channels": 6,
            "bitrate_kbps": 5000
        }
    elif "720p_avc" in file_path:
        return {
            "file_path": file_path,
            "video_codec": "AVC",
            "resolution": "1280x720",
            "audio_channels": 2,
            "bitrate_kbps": 2500
        }
    elif "2160p_hevc_8ch" in file_path:
        return {
            "file_path": file_path,
            "video_codec": "HEVC",
            "resolution": "3840x2160",
            "audio_channels": 8,
            "bitrate_kbps": 12000
        }
    else:
        # Default/unwanted file
        return {
            "file_path": file_path,
            "video_codec": "MPEG",
            "resolution": "640x480",
            "audio_channels": 2,
            "bitrate_kbps": 800
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
    of media file paths found.
    """
    monitored_paths = config_manager.get("monitored_paths", [])
    
    if not monitored_paths:
        return []

    found_files = []
    
    # MOCK IMPLEMENTATION: Simulating scan across configured paths
    for path in monitored_paths:
        # Generating deterministic mock data based on the monitored path
        if "Movies" in path:
            found_files.extend([
                f"{path}/IronMan_1080p_hevc.mkv",
                f"{path}/Avengers_720p_avc.mp4"
            ])
        elif "Shows" in path:
            found_files.extend([
                f"{path}/Series1_2160p_hevc_8ch.mkv",
                f"{path}/OldSeries_640p_mpeg.mov"
            ])
    
    print(f"Scanned paths: {monitored_paths}. Found {len(found_files)} files.")
    return found_files


@app.post("/get-metadata", response_model=Dict[str, Any])
def get_file_metadata_endpoint(file_info: FilePath) -> Dict[str, Any]:
    """
    Retrieves detailed metadata for a single file using a simulated ffprobe utility.
    """
    file_path = file_info.file_path
    
    # Simulate the actual metadata extraction
    metadata = _simulate_ffprobe(file_path)
    
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Metadata not found for file: {file_path}")
    
    return metadata
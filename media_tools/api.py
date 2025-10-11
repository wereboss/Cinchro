# media_tools/api.py

import os
import json
import logging
import subprocess
import re
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

def _get_live_ffprobe_metadata(file_path: str) -> Dict[str, Any]:
    """
    Executes the ffprobe command to get REAL structured media metadata,
    using robust parsing logic for the returned JSON structure.
    """
    logger.info(f"Executing ffprobe for file: {file_path}")
    
    # We add '-show_format' to get the overall bitrate (bit_rate) and duration
    command = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0,a:0',
        '-show_entries', 'stream=codec_name,width,height,channels,bit_rate',
        '-show_format',  # Request overall format info for total bitrate
        '-of', 'json',
        file_path
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        # DEBUGGING: Log the raw JSON output for inspection
        logger.info(f"FFPROBE RAW OUTPUT: {result.stdout.strip()}")

        data = json.loads(result.stdout)
        
        metadata = {
            "file_path": file_path,
            "video_codec": None,
            "resolution": None,
            "audio_channels": 0,
            "bitrate_kbps": 0
        }

        # 1. Iterate through streams to extract video and audio data
        for stream in data.get('streams', []):
            # Check for Video Stream: If it has width/height, it's video
            if stream.get('width') and stream.get('height'):
                metadata['video_codec'] = stream.get('codec_name', '').upper()
                metadata['resolution'] = f"{stream['width']}x{stream['height']}"
            
            # Check for Audio Stream: If it has channels, it's audio (and not already identified as video)
            elif stream.get('channels'):
                channels = stream.get('channels', 0)
                # Keep the max channel count if multiple audio streams are found
                if channels > metadata['audio_channels']:
                    metadata['audio_channels'] = channels
            
            # Use stream bit_rate if present, preferring it over overall format bitrate
            if 'bit_rate' in stream and stream['bit_rate']:
                metadata['bitrate_kbps'] = max(metadata['bitrate_kbps'], int(stream['bit_rate']) // 1000)

        # 2. Fallback: Use overall format bitrate if individual stream bitrates are missing
        if metadata['bitrate_kbps'] == 0 and data.get('format', {}).get('bit_rate'):
            metadata['bitrate_kbps'] = int(data['format']['bit_rate']) // 1000
            
        return metadata

    except subprocess.CalledProcessError as e:
        logger.error(f"ffprobe failed for {file_path}. Error: {e.stderr.strip()}")
        if "command not found" in e.stderr.lower() or "no such file or directory" in e.stderr.lower():
             raise HTTPException(status_code=500, detail="FFPROBE_NOT_FOUND: ffprobe utility is not installed or not in PATH.")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error during ffprobe parsing: {e}")
        return {}


# --- FastAPI Application ---

app = FastAPI(title="Cinchro Media Tools API", version="0.1.0")


@app.get("/status", response_model=Dict[str, str])
def get_service_status():
    """Returns the operational status of the Media Tools service."""
    return {"status": "ok", "service": "Cinchro Media Tools", "machine": "Unix"}


@app.get("/scan-files", response_model=List[str])
def scan_media_paths() -> List[str]:
    # ... (scan_media_paths function remains the same, it is already live) ...
    monitored_paths = config_manager.get("monitored_paths", [])
    all_found_files = [] 
    
    logger.info(f"Executing REAL file system scan for: {monitored_paths}")

    for path in monitored_paths:
        try:
            if not os.path.isdir(path):
                logger.warning(f"Monitored path does not exist or is inaccessible: {path}")
                continue

            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                
                if os.path.isfile(full_path):
                    # Filter for common media extensions
                    if item.lower().endswith(('.mkv', '.mp4', '.mov')):
                        all_found_files.append(full_path)

        except PermissionError:
            logger.error(f"Permission denied accessing path: {path}")
        except Exception as e:
            logger.error(f"Error during scan of {path}: {e}")
    
    logger.info(f"Scan complete. Found {len(all_found_files)} files.")
    return all_found_files 


@app.post("/get-metadata", response_model=Dict[str, Any])
def get_file_metadata_endpoint(file_info: FilePath) -> Dict[str, Any]:
    """
    Retrieves detailed metadata for a single file using the real ffprobe utility.
    """
    file_path = file_info.file_path
    
    # *** Live ffprobe call ***
    metadata = _get_live_ffprobe_metadata(file_path)
    
    if not metadata:
        # If metadata processing fails, still return a 404 or 500
        raise HTTPException(status_code=500, detail=f"Failed to process metadata for file: {file_path}")
    
    return metadata
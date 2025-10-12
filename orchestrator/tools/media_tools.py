# orchestrator/tools/media_tools.py

import json
import requests
from typing import List, Dict, Any

class MediaTools:
    """
    A collection of tools for the Cinchro Orchestrator to interact with the
    remote Media Tools service (Unix Machine) via REST API calls.
    """

    def __init__(self, api_base_url, use_dummy_data=False):
        """Initializes the tool client with the base URL of the remote API."""
        self.api_base_url = api_base_url
        self.use_dummy_data = use_dummy_data
        print(f"MediaTools initialized. Use dummy data: {self.use_dummy_data}")

    def list_media_files(self, location: str = "") -> List[str]:
        """
        Tool: Fetches a list of media files from the remote service.
        NOTE: The location parameter is now deprecated/ignored in the API call, 
              but kept in the function signature for compatibility.
        """
        if self.use_dummy_data:
            print(f"MOCK: Returning hardcoded file list.")
            # Hardcoded dummy data remains as a fallback/test case
            dummy_files = [
                f"{location}/movie_1080p_hevc.mkv",
                f"{location}/episode_720p_avc.mp4",
                f"{location}/home_video_480p_avi.mov"
            ]
            return dummy_files
        
        else:
            # FIX: Use the correct live API endpoint: /scan-files
            endpoint = f"{self.api_base_url}/scan-files"
            try:
                response = requests.get(endpoint)
                response.raise_for_status()  # Raise an HTTPError for bad status codes
                
                # Check for a 404 (Not Found) or 405 (Method Not Allowed) from the API
                if response.status_code == 404:
                    print(f"ERROR: Endpoint not found. Check if Media Tools service is running at {endpoint}")
                    return []
                
                return response.json()
            except requests.exceptions.RequestException as e:
                print(f"ERROR: Failed to connect to Media Tools API at {endpoint}. Error: {e}")
                return []

    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Tool: Retrieves detailed metadata for a specific media file from the remote service.
        """
        if self.use_dummy_data:
            print(f"MOCK: Returning hardcoded metadata for file: {file_path}")
            # Mocked metadata remains for testing purposes
            if "1080p_hevc" in file_path:
                return {"video_codec": "HEVC", "resolution": "1920x1080", "audio_channels": 8}
            else:
                return {"video_codec": "AVC", "resolution": "1280x720", "audio_channels": 2}
        
        else:
            endpoint = f"{self.api_base_url}/get-metadata"
            try:
                response = requests.post(endpoint, json={"file_path": file_path})
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                print(f"ERROR: Failed to fetch metadata from {endpoint}. Error: {e}")
                return {}
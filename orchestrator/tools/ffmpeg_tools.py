# orchestrator/tools/ffmpeg_tools.py

import json
import requests
from typing import Dict, Any

class FFMPEGGTools:
    """
    A collection of tools for the Cinchro Orchestrator to interact with the
    remote FFMPEG processing service (Linux Machine) via REST API calls.
    """

    def __init__(self, api_base_url, use_dummy_data=False):
        """Initializes the tool client with the base URL of the remote API."""
        self.api_base_url = api_base_url
        self.use_dummy_data = use_dummy_data
        print(f"FFMPEGGTools initialized. Use dummy data: {self.use_dummy_data}")

    def run_ffmpeg_command(self, command: str, input_file: str, output_file: str) -> Dict[str, Any]:
        """
        Tool: Executes an FFMPEG job on the remote Linux machine via the /submit-job endpoint.
        The output_file parameter is technically ignored as the Linux service determines it, 
        but we pass the required inputs.
        """
        if self.use_dummy_data:
            print(f"MOCK: Submitting dummy job for: {input_file}")
            # Simulating a successful job submission with dummy data
            job_id = "job_" + str(hash(input_file))
            return {
                "status": "COMPLETED",
                "job_id": job_id,
                "progress_percent": 100.0,
                "notes": "Mock job finished."
            }
        
        else:
            # FIX: Use the correct live API endpoint: /submit-job
            endpoint = f"{self.api_base_url}/submit-job"
            
            # The API expects input_file and ffmpeg_command in the JSON body
            payload = {
                "input_file": input_file,
                "ffmpeg_command": command
            }
            
            try:
                # Use POST to submit the job
                response = requests.post(endpoint, json=payload)
                response.raise_for_status() # Raise an HTTPError for bad status codes
                
                return response.json()
            except requests.exceptions.RequestException as e:
                print(f"CRITICAL ERROR: Failed to connect to FFMPEG API at {endpoint}. Error: {e}")
                return {"status": "FAILED", "job_id": "none", "notes": str(e)}

# --- No __main__ block needed here ---
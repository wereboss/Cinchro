# orchestrator/tools/media_tools.py

import json
import random

class MediaTools:
    """
    A collection of tools for the Cinchro Agent to interact with the
    remote media management service on the Unix machine.
    """

    def __init__(self, api_base_url, use_dummy_data=False):
        """Initializes the tool client with the base URL of the remote API."""
        self.api_base_url = api_base_url
        self.use_dummy_data = use_dummy_data
        print(f"MediaTools initialized. Use dummy data: {self.use_dummy_data}")

    def list_media_files(self, location: str) -> list:
        """
        Tool: Lists media files in a given directory.
        
        Args:
            location (str): The path to the directory to scan.
            
        Returns:
            list: A list of file paths.
        """
        if self.use_dummy_data:
            print(f"Using dummy data for list_media_files at location: {location}")
            # Simulating dummy data for testing the agent's logic
            dummy_files = [
                f"{location}/movie_1080p_hevc.mkv",
                f"{location}/episode_720p_avc.mp4",
                f"{location}/home_video_480p_avi.mov",
                f"{location}/concert_2160p_hevc.mkv"
            ]
            return dummy_files
        
        else:
            print(f"Making real API call to {self.api_base_url}/list_files at location: {location}")
            # In the future, this is where the real API call logic will go.
            # Example: requests.get(f"{self.api_base_url}/list_files?location={location}")
            return []

    def get_file_metadata(self, file_path: str) -> dict:
        """
        Tool: Retrieves detailed metadata for a specific media file.
        
        Args:
            file_path (str): The path of the file to inspect.
            
        Returns:
            dict: A dictionary containing the file's metadata.
        """
        if self.use_dummy_data:
            print(f"Using dummy data for get_file_metadata for file: {file_path}")
            # Simulating different metadata based on the dummy file paths
            if "1080p_hevc" in file_path:
                return {
                    "file_path": file_path,
                    "video_codec": "HEVC",
                    "resolution": "1920x1080",
                    "audio_channels": 8
                }
            elif "720p_avc" in file_path:
                return {
                    "file_path": file_path,
                    "video_codec": "AVC",
                    "resolution": "1280x720",
                    "audio_channels": 2
                }
            elif "2160p_hevc" in file_path:
                return {
                    "file_path": file_path,
                    "video_codec": "HEVC",
                    "resolution": "3840x2160",
                    "audio_channels": 6
                }
            else:
                return {
                    "file_path": file_path,
                    "video_codec": "MPEG-4",
                    "resolution": "640x480",
                    "audio_channels": 2
                }
        
        else:
            print(f"Making real API call to {self.api_base_url}/get_metadata for file: {file_path}")
            # In the future, this is where the real API call logic will go.
            return {}
            
if __name__ == '__main__':
    # Example usage with dummy data
    print("--- Testing with dummy data ---")
    tools = MediaTools(api_base_url="http://unix_machine_ip:5000", use_dummy_data=True)
    files = tools.list_media_files(location="/media/movies")
    print(f"Files found: {files}")
    
    metadata = tools.get_file_metadata(files[0])
    print(f"Metadata for {files[0]}: {metadata}")
    
    # Example usage without dummy data (simulating real API)
    print("\n--- Testing with real API (no dummy data) ---")
    real_tools = MediaTools(api_base_url="http://unix_machine_ip:5000", use_dummy_data=False)
    real_tools.list_media_files(location="/media/movies")
    real_tools.get_file_metadata(files[0])
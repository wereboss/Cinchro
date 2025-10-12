# orchestrator/engine.py

import os
import json
import sys
from typing import List

# Add the parent directory to the path to import sibling modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Cinchro Modules
from orchestrator.config import ConfigManager
from orchestrator.database import DatabaseManager
from orchestrator.tools.media_tools import MediaTools
from orchestrator.tools.ffmpeg_tools import FFMPEGGTools

class CinchroEngine:
    """
    The core, non-LLM orchestrator engine for Cinchro.
    It manages the entire media processing workflow deterministically.
    """

    def __init__(self, config_manager: ConfigManager):
        """Initializes the engine with its core components."""
        self.config_manager = config_manager
        self.db_manager = DatabaseManager(self.config_manager.get("DATABASE_PATH"))
        
        # Instantiate the tool wrappers
        self.media_tools = MediaTools(
            api_base_url=self.config_manager.get("media_api_url"),
            use_dummy_data=self.config_manager.get("use_dummy_tools")
        )
        self.ffmpeg_tools = FFMPEGGTools(
            api_base_url=self.config_manager.get("ffmpeg_api_url"),
            use_dummy_data=self.config_manager.get("use_dummy_tools")
        )

    def scan_and_add_files(self):
        """
        Calls the media tools API to get a list of files to monitor,
        and adds new ones to the database with a 'pending_evaluation' status.
        """
        print("--- Scanning for files via Media Tools API ---")
        # In a future version, this would be a new API endpoint on the media tools component.
        found_files = self.media_tools.list_media_files(location=self.config_manager.get("media_location"))
        
        for file_path in found_files:
            was_added = self.db_manager.add_file(file_path)
            if was_added:
                print(f"Discovered and added new file: {file_path}")
    
    def evaluate_files(self):
        """
        Evaluates files with a 'pending_scan' status against the updated
        standard (resolution > 480p) and updates their status.
        """
        print("--- Evaluating pending files ---")
        
        pending_files = self.db_manager.get_files_by_status('pending_scan')
        
        for file_path in pending_files:
            # Call metadata API (now works live)
            metadata = self.media_tools.get_file_metadata(file_path) 
            
            # --- UPDATED CINCHRO CRITERIA ---
            resolution_str = metadata.get('resolution', '0x0')
            height = 0
            
            # Safely extract height (the second number in WxH format)
            try:
                if 'x' in resolution_str:
                    height = int(resolution_str.split('x')[1])
            except (ValueError, IndexError):
                pass # If parsing fails, height remains 0

            # Cinchro New Standard: Must be greater than 480p
            is_good_resolution = height > 480
            
            # The target output codec is always H265/HEVC, so we look for files that are *not* already H265
            is_already_target_codec = metadata.get('video_codec', '').upper() in ('HEVC', 'H265')
            
            if is_good_resolution and not is_already_target_codec:
                new_status = 'ready_for_conversion'
                notes = f"Nominated: Resolution {resolution_str} > 480p, and needs HEVC conversion (currently {metadata.get('video_codec')})."
                print(f"File {file_path} is ready for conversion.")
            else:
                reason = []
                if not is_good_resolution:
                    reason.append(f"Resolution ({resolution_str}) is 480p or lower.")
                if is_already_target_codec:
                    reason.append(f"Already {metadata.get('video_codec')} codec (no conversion needed).")
                if not reason:
                    reason.append("Failed generic check.") # Fallback for unexpected case

                new_status = 'skipped'
                notes = f"Skipped: {' '.join(reason)}"
                print(f"File {file_path} skipped.")

            self.db_manager.update_file_status(file_path, new_status, notes=notes)




    def process_ready_files(self):
        """
        Automatically processes files that are ready for conversion.
        """
        print("--- Starting automated conversion process ---")
        ready_files = self.db_manager.get_files_by_status('ready_for_conversion')
        
        for file_path in ready_files:
            # Example conversion logic and command
            output_file = file_path.replace(".mkv", ".mp4")
            command = f"ffmpeg -i '{file_path}' -c:v copy -c:a aac -b:a 192k '{output_file}'"
            
            print(f"Initiating conversion for: {file_path}")
            job_info = self.ffmpeg_tools.run_ffmpeg_command(command, file_path, output_file)
            
            # Update database status
            self.db_manager.update_file_status(
                file_path, 
                'processing', 
                processing_path=job_info.get('output_file'),
                notes=f"Job submitted: {job_info.get('job_id')}"
            )

    def run_full_workflow(self):
        """Runs the entire Cinchro workflow in sequence."""
        self.scan_and_add_files()
        self.evaluate_files()
        self.process_ready_files()
        print("\n--- Workflow finished. ---")


if __name__ == "__main__":
    # --- Example Usage ---
    # Create dummy config files for demonstration
    with open("config.json", "w") as f:
        json.dump({
            "media_api_url": "http://media-tools:5000",
            "ffmpeg_api_url": "http://ffmpeg-tools:5001",
            "use_dummy_tools": True,
            "media_location": "/media/cinchro/library"
        }, f)
    with open(".env", "w") as f:
        f.write("DATABASE_PATH=./cinchro.db\n")
    
    # 1. Initialize the engine
    print("Initializing Cinchro Engine...")
    config_manager = ConfigManager()
    engine = CinchroEngine(config_manager)
    
    # 2. Run the workflow
    engine.run_full_workflow()
    
    # 3. Clean up dummy files
    os.remove("config.json")
    os.remove(".env")
    os.remove("cinchro.db")
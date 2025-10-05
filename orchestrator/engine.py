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
        Evaluates files with a 'pending_evaluation' status against predefined
        quality metrics and updates their status.
        """
        print("--- Evaluating pending files ---")
        pending_files = self.db_manager.get_files_by_status('pending_evaluation')
        
        for file_path in pending_files:
            metadata = self.media_tools.get_file_metadata(file_path)
            
            # Predefined evaluation rules
            is_high_res = "1920x1080" in metadata.get('resolution', '')
            is_hevc = metadata.get('video_codec', '').upper() == 'HEVC'
            
            if is_high_res and is_hevc:
                new_status = 'ready_for_conversion'
                notes = "Meets all quality standards."
                print(f"File {file_path} is ready for conversion.")
            else:
                new_status = 'skipped'
                notes = "Does not meet quality standards (not high-res or HEVC)."
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
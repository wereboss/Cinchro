# orchestrator/main.py

import os
import sys
import time
import errno
from datetime import datetime

# Add the parent directory to the path to import sibling modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrator.config import ConfigManager
from orchestrator.engine import CinchroEngine

if __name__ == "__main__":
    """
    Main entry point for the Cinchro Orchestrator application.
    This version includes a file-based lock for single-instance control
    and runs the workflow without user inputs.
    """
    print("--- Cinchro Orchestrator: Starting Up ---")
    
    # Define file paths for configuration and lock file
    orchestrator_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(orchestrator_dir, 'config.json')
    env_path = os.path.join(orchestrator_dir, '.env')
    lock_path = os.path.join(orchestrator_dir, 'cinchro.lock')
    
    # 1. Single-Instance Lock Mechanism
    try:
        # Create and acquire a lock file
        lock_file = open(lock_path, 'x')
    except IOError as e:
        if e.errno == errno.EEXIST:
            print("Another instance of the orchestrator is already running. Exiting.")
            sys.exit(0)
        else:
            print(f"Error creating lock file: {e}")
            sys.exit(1)

    # 2. Initialize Configuration
    try:
        config_manager = ConfigManager(config_path=config_path, env_path=env_path)
        print("Configuration loaded successfully.")
    except Exception as e:
        print(f"Error loading configuration: {e}")
        lock_file.close()
        os.remove(lock_path)
        sys.exit(1)
        
    # 3. Instantiate and Run the Engine
    try:
        cinchro_engine = CinchroEngine(config_manager)
        print("Cinchro Engine initialized. Starting automated workflow...")
        
        cinchro_engine.run_full_workflow()
        
        print("\n--- Cinchro Orchestrator: Workflow Completed ---")
        
    except Exception as e:
        print(f"\nAn unexpected error occurred during workflow execution: {e}")
        # Add more specific logging here in a production environment
        sys.exit(1)
    finally:
        # 4. Clean up the lock file
        lock_file.close()
        os.remove(lock_path)

    print(f"Cinchro Orchestrator shutdown at: {datetime.now().isoformat()}")
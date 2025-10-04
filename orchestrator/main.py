# orchestrator/main.py

import os
import json
import sys
from datetime import datetime

# Add the parent directory to the path to import sibling modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrator.config import ConfigManager
from orchestrator.agent import CinchroAgent

if __name__ == "__main__":
    """
    Main entry point for the Cinchro Orchestrator application.
    """
    print("--- Cinchro Orchestrator: Starting Up ---")
    
    # Define file paths for configuration
    orchestrator_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(orchestrator_dir, 'config.json')
    env_path = os.path.join(orchestrator_dir, '.env')
    
    # 1. Initialize Configuration
    try:
        config_manager = ConfigManager(config_path=config_path, env_path=env_path)
        print("Configuration loaded successfully.")
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)
        
    # 2. Instantiate and Run the Agent
    try:
        cinchro_agent = CinchroAgent()
        print("Cinchro Agent initialized. Starting workflow...")
        cinchro_agent.run()
        print("\n--- Cinchro Orchestrator: Workflow Completed ---")
        
    except Exception as e:
        print(f"\nAn unexpected error occurred during workflow execution: {e}")
        # Add more specific logging here in a production environment
        sys.exit(1)

    print(f"Cinchro Orchestrator shutdown at: {datetime.now().isoformat()}")
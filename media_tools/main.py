# media_tools/main.py

import uvicorn
import os
import sys
import json

# Ensure local imports work by setting up the path (standard practice)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from media_tools.api import app
from media_tools.config import ConfigManager

if __name__ == "__main__":
    """
    Main entry point for the Cinchro Media Tools service.
    Loads configuration and starts the Uvicorn server.
    """
    
    print("--- Cinchro Media Tools Service: Starting Up ---")
    
    # Define file paths for configuration
    service_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(service_dir, 'config.json')
    env_path = os.path.join(service_dir, '.env')
    
    # 1. Initialize Configuration
    try:
        config_manager = ConfigManager(config_path=config_path, env_path=env_path)
        
        HOST = config_manager.get("api_host", "0.0.0.0")
        PORT = int(config_manager.get("api_port", 5000))

        print(f"Configuration loaded. Service starting on {HOST}:{PORT}")
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    # 2. Start Uvicorn Server
    try:
        uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    except Exception as e:
        print(f"Uvicorn server failed to start: {e}")
        sys.exit(1)
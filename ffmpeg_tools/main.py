# ffmpeg_tools/main.py

import uvicorn
import os
import sys
from typing import Optional

# Add the parent directory to the path for local module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ffmpeg_tools.api import app
from ffmpeg_tools.config import ConfigManager

if __name__ == "__main__":
    """
    Main entry point for the Cinchro FFMPEG Tools service.
    Loads configuration and starts the Uvicorn server on the Linux machine.
    """
    
    print("--- Cinchro FFMPEG Tools Service: Starting Up ---")
    
    # Define file paths for configuration
    service_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(service_dir, 'config.json')
    env_path = os.path.join(service_dir, '.env')
    
    # 1. Initialize Configuration
    try:
        config_manager = ConfigManager(config_path=config_path, env_path=env_path)
        
        HOST: str = config_manager.get("api_host", "0.0.0.0")
        PORT: int = int(config_manager.get("api_port", 5001))

        print("Configuration loaded successfully.")
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    # 2. Start Uvicorn Server
    try:
        print(f"Service starting on {HOST}:{PORT}")
        uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    except Exception as e:
        print(f"Uvicorn server failed to start: {e}")
        sys.exit(1)
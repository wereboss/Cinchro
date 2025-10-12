# ffmpeg_tools/config.py

import os
import json
from dotenv import load_dotenv

class ConfigManager:
    """
    Manages the FFMPEG Tools application's configuration by loading settings 
    from a config.json file and environment variables from a .env file.
    """

    def __init__(self, config_path="config.json", env_path=".env"):
        """
        Initializes the ConfigManager, loading both config.json and .env files.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        abs_config_path = os.path.join(base_dir, config_path)
        abs_env_path = os.path.join(base_dir, env_path)
        
        load_dotenv(dotenv_path=abs_env_path)
        
        self.config_data = {}
        try:
            with open(abs_config_path, 'r') as f:
                self.config_data = json.load(f)
        except FileNotFoundError:
            print(f"Warning: The configuration file '{abs_config_path}' was not found. "
                  "Continuing with default and environment variables only.")
        except json.JSONDecodeError:
            print(f"Error: The configuration file '{abs_config_path}' is not a valid JSON file.")

    def get(self, key, default=None):
        """
        Retrieves a configuration value. It first checks environment variables
        and then falls back to the loaded JSON configuration.
        """
        # Prioritize environment variables
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value
        
        # We need to handle nested configuration manually if we don't know the nesting depth.
        # However, for our known structure, we assume top-level or single-level dictionary access.
        
        # Check top level config
        if key in self.config_data:
            return self.config_data[key]
        
        # Check nested structures explicitly (e.g., "media_machine_config.storage_host")
        if '.' in key:
            parts = key.split('.')
            current_level = self.config_data
            try:
                for part in parts:
                    if isinstance(current_level, dict):
                        current_level = current_level[part]
                    else:
                        return default
                return current_level
            except KeyError:
                pass

        return self.config_data.get(key, default)
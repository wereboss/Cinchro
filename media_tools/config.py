# media_tools/config.py

import os
import json
from dotenv import load_dotenv

class ConfigManager:
    """
    Manages the Media Tools application's configuration by loading settings 
    from a config.json file and environment variables from a .env file.
    """

    def __init__(self, config_path="config.json", env_path=".env"):
        """
        Initializes the ConfigManager, loading both config.json and .env files.
        """
        # Load environment variables from the .env file
        load_dotenv(dotenv_path=env_path)
        
        self.config_data = {}
        # Load configuration from the config.json file
        try:
            with open(config_path, 'r') as f:
                self.config_data = json.load(f)
        except FileNotFoundError:
            print(f"Warning: The configuration file '{config_path}' was not found. "
                  "Continuing with default and environment variables only.")
        except json.JSONDecodeError:
            print(f"Error: The configuration file '{config_path}' is not a valid JSON file.")

    def get(self, key, default=None):
        """
        Retrieves a configuration value. It first checks environment variables
        and then falls back to the loaded JSON configuration.
        """
        # Prioritize environment variables
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value

        # Fallback to the JSON configuration
        return self.config_data.get(key, default)

    def get_json_content(self):
        """
        Returns the entire dictionary loaded from the config.json file.
        """
        return self.config_data

    def get_env_variables(self):
        """
        Returns all environment variables loaded from the .env file.
        """
        return os.environ

if __name__ == "__main__":
    # --- Example Usage (requires local dummy files) ---
    print("This file contains the foundational ConfigManager class for the Media Tools service.")
# tests/orchestrator/test_config.py

import os
import sys
import pytest

from orchestrator.config import ConfigManager


def test_config_manager_loads_both_files(test_config_files):
    """
    Tests that the ConfigManager correctly loads values from both
    config.json and .env files.
    """
    config_manager = ConfigManager(
        config_path=os.path.join(test_config_files, 'config.json'),
        env_path=os.path.join(test_config_files, '.env')
    )
    
    # Assert that a value from the .env file is loaded
    assert config_manager.get('DATABASE_PATH') is not None
    
    # Assert that a value from the config.json file is loaded
    assert config_manager.get('LLM_MODEL') == 'test_model'

def test_env_variables_override_json(test_config_files):
    """
    Tests that values in the .env file take precedence over
    values with the same key in config.json.
    """
    # Overwrite a value in the temporary .env file for this test
    env_path = os.path.join(test_config_files, '.env')
    with open(env_path, 'a') as f:
        f.write("\nLLM_MODEL=env_test_model_override")
        
    config_manager = ConfigManager(
        config_path=os.path.join(test_config_files, 'config.json'),
        env_path=env_path
    )
    
    # Assert that the value from .env is returned, not the JSON one
    assert config_manager.get('LLM_MODEL') == 'env_test_model_override'

def test_get_method_with_default_value(test_config_files):
    """
    Tests that the get() method returns the default value
    when a key is not found.
    """
    config_manager = ConfigManager(
        config_path=os.path.join(test_config_files, 'config.json'),
        env_path=os.path.join(test_config_files, '.env')
    )
    
    # Test with a key that does not exist in either file
    assert config_manager.get('NON_EXISTENT_KEY', 'default') == 'default'
    assert config_manager.get('NON_EXISTENT_KEY') is None
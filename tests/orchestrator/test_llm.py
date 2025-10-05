# tests/orchestrator/test_llm.py

import pytest
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool

# Import the ConfigManager class from our orchestrator module
from orchestrator.config import ConfigManager

# Define a simple, dummy tool for testing purposes
@tool
def get_hello_world_message(name: str) -> str:
    """A simple tool that returns a greeting."""
    return f"Hello, {name}!"

def test_gemini_instance_and_tool_binding(test_config_files):
    """
    Tests that a ChatGoogleGenerativeAI instance can be created and a tool
    can be successfully bound to it using a secure config pipeline.
    """
    try:
        # Explicitly load the .env file from the temporary directory
        env_path = os.path.join(test_config_files, '.env')
        load_dotenv(dotenv_path=env_path)

        # Instantiate our ConfigManager to load the dummy .env and config.json
        config_manager = ConfigManager(
            config_path=os.path.join(test_config_files, 'config.json'),
            env_path=env_path
        )
        
        # Get the API key from the ConfigManager
        google_api_key = config_manager.get('GOOGLE_API_KEY')
        assert google_api_key is not None

        # Create an instance of the LLM using the retrieved key
        llm = ChatGoogleGenerativeAI(
            model="gemini-pro-1.5",
            google_api_key=google_api_key
        )
        
        # Bind the dummy tool to the LLM
        llm_with_tool = llm.bind_tools([get_hello_world_message])
        
        # Assert that the Runnable object has at least one tool
        assert len(llm_with_tool.bound.tools) > 0
        
        print("\nTest passed: ChatGoogleGenerativeAI instance created and tool bound successfully.")
        
    except Exception as e:
        pytest.fail(f"An error occurred during LLM instantiation or tool binding: {e}")
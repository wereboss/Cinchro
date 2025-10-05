# tests/orchestrator/test_agent.py

import os
import sys
import json
import pytest
from unittest.mock import MagicMock

# The updated import path based on our findings
from orchestrator.agent import CinchroAgent
from orchestrator.database import DatabaseManager

# Add the project root to the sys.path to allow for relative imports in this test file
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


@pytest.fixture
def mock_tools():
    """Mocks the tools used by the agent."""
    mock_media_tools = MagicMock()
    mock_ffmpeg_tools = MagicMock()
    return mock_media_tools, mock_ffmpeg_tools

@pytest.fixture
def mock_db():
    """Mocks the database manager."""
    return MagicMock(spec=DatabaseManager)

@pytest.fixture
def agent(mock_tools, mock_db):
    """Initializes the CinchroAgent with mocked dependencies."""
    mock_media_tools, mock_ffmpeg_tools = mock_tools
    return CinchroAgent(
        database_manager=mock_db,
        media_tools=mock_media_tools,
        ffmpeg_tools=mock_ffmpeg_tools
    )

def test_scan_media_node(agent, mock_tools, mock_db):
    """Tests that the scan_media_node correctly lists new files and adds them to the database."""
    mock_media_tools, _ = mock_tools
    
    # Mock the list_media_files method to return a dummy list
    dummy_files = ["/media/file1.mkv", "/media/file2.mkv"]
    mock_media_tools.list_media_files.return_value = dummy_files
    
    # Execute the node
    initial_state = {}
    next_state = agent.scan_media_node(initial_state)

    # Assert that the tool was called and the database was updated
    mock_media_tools.list_media_files.assert_called_once()
    assert next_state['new_files'] == dummy_files
    for file_path in dummy_files:
        mock_db.add_file.assert_any_call(file_path)

def test_evaluate_file_node_positive_case(agent, mock_tools, mock_db):
    """Tests a positive evaluation case where a file meets the criteria for processing."""
    mock_media_tools, _ = mock_tools
    
    # Mock the get_file_metadata tool to return a "good" file
    mock_metadata = {
        "file_path": "/media/test_good_file.mkv",
        "video_codec": "hevc",
        "resolution": "1920x1080"
    }
    mock_media_tools.get_file_metadata.return_value = mock_metadata
    
    # Mock the LLM decision to be "yes"
    agent.llm_decision_chain = MagicMock(return_value="yes")
    
    # Execute the node with a file to evaluate
    initial_state = {"file_to_evaluate": "/media/test_good_file.mkv"}
    next_state = agent.evaluate_file_node(initial_state)

    # Assert the correct return state and database update
    assert next_state['file_to_evaluate'] == mock_metadata['file_path']
    assert next_state['next'] == "evaluation_passed"
    mock_db.update_file_status.assert_called_once_with(
        mock_metadata['file_path'], 'evaluation_passed'
    )

def test_evaluate_file_node_negative_case(agent, mock_tools, mock_db):
    """Tests a negative evaluation case where a file does not meet the criteria."""
    mock_media_tools, _ = mock_tools
    
    # Mock the get_file_metadata tool to return a "bad" file
    mock_metadata = {
        "file_path": "/media/test_bad_file.mkv",
        "video_codec": "avc",
        "resolution": "1280x720"
    }
    mock_media_tools.get_file_metadata.return_value = mock_metadata
    
    # Mock the LLM decision to be "no"
    agent.llm_decision_chain = MagicMock(return_value="no")
    
    # Execute the node with a file to evaluate
    initial_state = {"file_to_evaluate": "/media/test_bad_file.mkv"}
    next_state = agent.evaluate_file_node(initial_state)
    
    # Assert the correct return state and database update
    assert next_state['file_to_evaluate'] == mock_metadata['file_path']
    assert next_state['next'] == "evaluation_skipped"
    mock_db.update_file_status.assert_called_once_with(
        mock_metadata['file_path'], 'skipped', notes="File evaluation resulted in 'no'."
    )
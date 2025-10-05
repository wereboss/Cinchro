# tests/orchestrator/test_engine.py

import pytest
from unittest.mock import MagicMock
import sys
import os

# Adjust the Python path to allow for imports from the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from orchestrator.engine import CinchroEngine
from orchestrator.config import ConfigManager
from orchestrator.database import DatabaseManager
from orchestrator.tools.media_tools import MediaTools
from orchestrator.tools.ffmpeg_tools import FFMPEGGTools


@pytest.fixture
def mock_dependencies():
    """Provides mocked instances of all external dependencies."""
    return {
        'config_manager': MagicMock(spec=ConfigManager),
        'db_manager': MagicMock(spec=DatabaseManager),
        'media_tools': MagicMock(spec=MediaTools),
        'ffmpeg_tools': MagicMock(spec=FFMPEGGTools)
    }

@pytest.fixture
def engine(mock_dependencies):
    """Initializes and returns a CinchroEngine instance with mocked dependencies."""
    mock_dependencies['config_manager'].get.side_effect = lambda key: {
        "DATABASE_PATH": "test.db",
        "media_api_url": "http://mock-media",
        "ffmpeg_api_url": "http://mock-ffmpeg",
        "use_dummy_tools": True
    }.get(key)
    
    # We will override the engine's __init__ to use our mocks directly
    engine_instance = CinchroEngine.__new__(CinchroEngine)
    engine_instance.config_manager = mock_dependencies['config_manager']
    engine_instance.db_manager = mock_dependencies['db_manager']
    engine_instance.media_tools = mock_dependencies['media_tools']
    engine_instance.ffmpeg_tools = mock_dependencies['ffmpeg_tools']
    
    return engine_instance

def test_scan_and_add_files_discovers_new_files(engine, mock_dependencies):
    """
    Tests that the engine correctly scans for new files and adds them to the database.
    """
    mock_dependencies['media_tools'].list_media_files.return_value = ["/media/file1.mp4", "/media/file2.mov"]
    mock_dependencies['db_manager'].add_file.side_effect = [True, False] # Simulate file1 as new, file2 as existing
    
    engine.scan_and_add_files("/media/library")
    
    # Assert that the list_media_files tool was called once
    mock_dependencies['media_tools'].list_media_files.assert_called_once_with("/media/library")
    
    # Assert that add_file was called for both files
    mock_dependencies['db_manager'].add_file.assert_any_call("/media/file1.mp4")
    mock_dependencies['db_manager'].add_file.assert_any_call("/media/file2.mov")
    
    # Assert that add_file was called exactly twice
    assert mock_dependencies['db_manager'].add_file.call_count == 2

def test_evaluate_files_updates_status_correctly(engine, mock_dependencies):
    """
    Tests that the engine correctly evaluates files and updates their status.
    """
    mock_dependencies['db_manager'].get_files_by_status.return_value = ["/media/good.mkv", "/media/bad.mp4"]
    mock_dependencies['media_tools'].get_file_metadata.side_effect = [
        # Metadata for the 'good' file
        {"resolution": "1920x1080", "video_codec": "HEVC"},
        # Metadata for the 'bad' file
        {"resolution": "1280x720", "video_codec": "AVC"}
    ]
    
    engine.evaluate_files()
    
    # Assert that the status for the good file was updated correctly
    mock_dependencies['db_manager'].update_file_status.assert_any_call(
        "/media/good.mkv", 'ready_for_conversion', notes="Meets all quality standards."
    )
    
    # Assert that the status for the bad file was updated correctly
    mock_dependencies['db_manager'].update_file_status.assert_any_call(
        "/media/bad.mp4", 'skipped', notes="Does not meet quality standards (not high-res or HEVC)."
    )

def test_process_ready_files_with_confirmation(engine, mock_dependencies):
    """
    Tests that the engine processes files when user confirmation is provided.
    """
    mock_dependencies['db_manager'].get_files_by_status.return_value = ["/media/ready.mkv"]
    mock_dependencies['ffmpeg_tools'].run_ffmpeg_command.return_value = {"job_id": "job_123"}
    
    engine.process_ready_files("yes")
    
    # Assert that the FFMPEG tool was called
    mock_dependencies['ffmpeg_tools'].run_ffmpeg_command.assert_called_once()
    
    # Assert that the database status was updated to 'processing'
    mock_dependencies['db_manager'].update_file_status.assert_called_once()
    assert mock_dependencies['db_manager'].update_file_status.call_args[0][1] == 'processing'
    
def test_process_ready_files_without_confirmation(engine, mock_dependencies):
    """
    Tests that the engine does NOT process files if user confirmation is denied.
    """
    mock_dependencies['db_manager'].get_files_by_status.return_value = ["/media/ready.mkv"]
    
    engine.process_ready_files("no")
    
    # Assert that the FFMPEG tool was never called
    mock_dependencies['ffmpeg_tools'].run_ffmpeg_command.assert_not_called()
    
    # Assert that no database status was updated to 'processing'
    for call in mock_dependencies['db_manager'].update_file_status.call_args_list:
        assert call.args[1] != 'processing'
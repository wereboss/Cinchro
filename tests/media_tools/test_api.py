# tests/media_tools/test_api.py

import pytest
from typing import Dict, Any

# Note: The api_client fixture is automatically available from conftest.py

def test_status_endpoint(api_client):
    """Verifies the health check endpoint works correctly."""
    response = api_client.get("/status")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Cinchro Media Tools", "machine": "Unix"}

def test_scan_files_returns_mock_paths(api_client):
    """
    Verifies that /scan-files correctly reads the paths from the mock config
    and returns the expected number of simulated files.
    """
    response = api_client.get("/scan-files")
    files = response.json()
    
    assert response.status_code == 200
    
    # Based on the mock config (2 paths, 2 files each)
    assert len(files) == 4
    
    # Check that paths are correctly generated
    assert "/mnt/media/Movies/IronMan_1080p_hevc.mkv" in files
    assert "/mnt/media/Shows/Series1_2160p_hevc_8ch.mkv" in files

def test_get_metadata_high_res_file(api_client):
    """
    Verifies the metadata for a file meeting high-res criteria.
    """
    test_file = "/mnt/media/Movies/IronMan_1080p_hevc.mkv"
    response = api_client.post(
        "/get-metadata", 
        json={"file_path": test_file}
    )
    metadata: Dict[str, Any] = response.json()
    
    assert response.status_code == 200
    assert metadata["file_path"] == test_file
    assert metadata["resolution"] == "1920x1080"
    assert metadata["video_codec"] == "HEVC"

def test_get_metadata_low_res_file(api_client):
    """
    Verifies the metadata for a file that fails the criteria (simulated low-res AVC).
    """
    test_file = "/mnt/media/Shows/OldSeries_640p_mpeg.mov"
    response = api_client.post(
        "/get-metadata", 
        json={"file_path": test_file}
    )
    metadata: Dict[str, Any] = response.json()
    
    assert response.status_code == 200
    assert metadata["file_path"] == test_file
    assert metadata["resolution"] == "640x480"
    assert metadata["video_codec"] == "MPEG"

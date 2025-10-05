# tests/orchestrator/test_database.py

import os
import sys
import pytest
import json


from orchestrator.database import DatabaseManager


def test_add_and_get_file(test_db):
    """
    Tests that a new file can be added to the database and its
    information can be retrieved correctly.
    """
    db_manager = DatabaseManager(test_db)
    file_path = "/media/test_file.mkv"
    
    # Add the file
    result = db_manager.add_file(file_path)
    assert result is True
    
    # Get the file info and assert its content
    info = db_manager.get_file_info(file_path)
    assert info is not None
    assert info['file_path'] == file_path
    assert info['status'] == 'pending_scan'
    
    db_manager.close()

def test_add_duplicate_file(test_db):
    """
    Tests that adding a duplicate file returns False and does not
    create a new row.
    """
    db_manager = DatabaseManager(test_db)
    file_path = "/media/duplicate_file.mkv"
    
    # Add the file the first time
    result_1 = db_manager.add_file(file_path)
    assert result_1 is True
    
    # Add the same file again
    result_2 = db_manager.add_file(file_path)
    assert result_2 is False
    
    # Check that only one row exists in the database
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM media_files WHERE file_path = ?", (file_path,))
    count = cursor.fetchone()[0]
    assert count == 1
    
    db_manager.close()

def test_update_file_status(test_db):
    """
    Tests that the file status and other fields can be updated correctly.
    """
    db_manager = DatabaseManager(test_db)
    file_path = "/media/update_test_file.mkv"
    
    db_manager.add_file(file_path)
    
    new_status = 'processed'
    processing_path = '/tmp/processed_file.mp4'
    output_files = ["/output/final.mp4", "/output/final.srt"]
    notes = "Transcoded and organized"
    
    db_manager.update_file_status(
        file_path, new_status, processing_path, output_files, notes
    )
    
    info = db_manager.get_file_info(file_path)
    
    assert info['status'] == new_status
    assert info['processing_file_path'] == processing_path
    assert json.loads(info['output_files']) == output_files
    assert info['notes'] == notes
    assert info['last_processed_date'] is not None
    
    db_manager.close()

def test_get_files_by_status(test_db):
    """
    Tests that files can be correctly retrieved based on their status.
    """
    db_manager = DatabaseManager(test_db)
    
    # Add files with different statuses
    db_manager.add_file("/media/file1.mkv")
    db_manager.add_file("/media/file2.mkv")
    db_manager.add_file("/media/file3.mkv")
    db_manager.update_file_status("/media/file2.mkv", 'processed')
    db_manager.update_file_status("/media/file3.mkv", 'skipped')
    
    pending_files = db_manager.get_files_by_status('pending_scan')
    processed_files = db_manager.get_files_by_status('processed')
    skipped_files = db_manager.get_files_by_status('skipped')
    
    assert len(pending_files) == 1
    assert "/media/file1.mkv" in pending_files
    
    assert len(processed_files) == 1
    assert "/media/file2.mkv" in processed_files
    
    assert len(skipped_files) == 1
    assert "/media/file3.mkv" in skipped_files

    db_manager.close()
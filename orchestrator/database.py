# orchestrator/database.py

import sqlite3
import json
from datetime import datetime

class DatabaseManager:
    """
    Manages the central SQLite database for the Cinchro orchestrator.
    This database tracks the state of every media file.
    """

    def __init__(self, db_path):
        """Initializes the DatabaseManager and ensures the tables exist."""
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        """Creates the media_files table if it doesn't already exist."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS media_files (
                file_path TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                last_processed_date TEXT,
                processing_file_path TEXT,
                output_files TEXT,
                notes TEXT
            );
        """)
        self.conn.commit()

    def add_file(self, file_path):
        """Adds a new file to the database with a 'pending_scan' status."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO media_files (file_path, status, last_processed_date)
                VALUES (?, ?, ?)
            """, (file_path, 'pending_scan', datetime.now().isoformat()))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # File already exists, no need to add
            return False

    def update_file_status(self, file_path, status, processing_path=None, output_files=None, notes=None):
        """
        Updates the status and other information for a given file.
        Output files are stored as a JSON string.
        """
        cursor = self.conn.cursor()
        output_files_json = json.dumps(output_files) if output_files is not None else None
        
        cursor.execute("""
            UPDATE media_files
            SET status = ?, 
                last_processed_date = ?,
                processing_file_path = ?,
                output_files = ?,
                notes = ?
            WHERE file_path = ?
        """, (status, datetime.now().isoformat(), processing_path, output_files_json, notes, file_path))
        self.conn.commit()

    def get_files_by_status(self, status):
        """Retrieves a list of file paths that match a given status."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT file_path FROM media_files WHERE status = ?", (status,))
        return [row[0] for row in cursor.fetchall()]

    def get_file_info(self, file_path):
        """Retrieves all stored information about a single file."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM media_files WHERE file_path = ?", (file_path,))
        row = cursor.fetchone()
        if row:
            # Convert row to a dictionary for easier access
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None

    def close(self):
        """Closes the database connection."""
        self.conn.close()

if __name__ == "__main__":
    # --- Example Usage ---
    
    # Instantiate the database manager
    db_manager = DatabaseManager("test_cinchro.db")
    
    # Add some dummy files
    files_to_add = ["/media/video1.mkv", "/media/video2.mkv", "/media/video3.mkv"]
    for file in files_to_add:
        db_manager.add_file(file)
    
    print("Files with 'pending_scan' status:")
    print(db_manager.get_files_by_status('pending_scan'))
    
    # Update the status of a file to 'processed'
    db_manager.update_file_status(
        file_path="/media/video1.mkv",
        status="processed",
        processing_path="/tmp/video1_transcode.mkv",
        output_files=["/output/video1.mp4", "/output/video1.srt"],
        notes="Transcoded successfully to MP4 and SRT"
    )

    print("\nInfo for /media/video1.mkv after processing:")
    info = db_manager.get_file_info("/media/video1.mkv")
    if info:
        # The output_files will be a JSON string, so we need to parse it back
        info['output_files'] = json.loads(info['output_files'])
        for key, value in info.items():
            print(f"- {key}: {value}")
            
    print("\nFiles with 'pending_scan' status now:")
    print(db_manager.get_files_by_status('pending_scan'))
    
    db_manager.close()
    
    # Clean up the test database file
    os.remove("test_cinchro.db")
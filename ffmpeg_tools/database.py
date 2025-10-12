# ffmpeg_tools/database.py

import sqlite3
from datetime import datetime
from typing import Dict, Any, List

class JobDatabaseManager:
    """
    Manages the local SQLite database for the FFMPEG Tools Job Manager.
    This database tracks the status and progress of all conversion jobs.
    """

    def __init__(self, db_path: str):
        """Initializes the database manager and ensures the jobs table exists."""
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        """Creates the conversion_jobs table."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversion_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                input_file TEXT NOT NULL,
                output_file TEXT NOT NULL,
                ffmpeg_command TEXT,
                rsync_user_host TEXT,
                progress_percent REAL,
                last_updated TEXT,
                notes TEXT
            );
        """)
        self.conn.commit()

    def create_job(self, job_id: str, input_file: str, output_file: str, ffmpeg_command: str):
        """Creates a new job entry with initial SUBMITTED status."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO conversion_jobs 
            (job_id, status, input_file, output_file, ffmpeg_command, progress_percent, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (job_id, 'SUBMITTED', input_file, output_file, ffmpeg_command, 0.0, now))
        self.conn.commit()

    def update_job_status(self, job_id: str, status: str, progress: float = None, notes: str = None):
        """Updates the status and progress of an existing job."""
        updates = []
        params = []
        
        updates.append("status = ?")
        params.append(status)
        
        if progress is not None:
            updates.append("progress_percent = ?")
            params.append(progress)
            
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
            
        updates.append("last_updated = ?")
        params.append(datetime.now().isoformat())
        
        params.append(job_id)
        
        cursor = self.conn.cursor()
        query = f"UPDATE conversion_jobs SET {', '.join(updates)} WHERE job_id = ?"
        cursor.execute(query, params)
        self.conn.commit()

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Retrieves a single job record."""
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM conversion_jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return {}
    
    def close(self):
        """Closes the database connection."""
        self.conn.close()

# --- Example usage block removed to keep the file clean for the package ---
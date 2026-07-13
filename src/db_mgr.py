import sqlite3
from pathlib import Path

DB_PATH = Path("database/tracker.db")

def get_db_connection():
    """
    Opens a connection to our SQLite database file.
    If the file tracker.db doesn't exist yet, SQLite will automatically create it!
    """
    conn = sqlite3.connect(DB_PATH)
    # This setting configures the connection to return rows like dictionary key-values
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """
    Creates the tracking table if it doesn't exist yet.
    Think of this exactly like running a script in MySQL Workbench.
    """
    # 1. Establish the connection line (like mysqli_connect in PHP)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 2. Execute the table creation SQL command
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posted_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL,
            posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # 3. Commit changes and close out the connection safely
    conn.commit()
    conn.close()
    print("🗄️ Database layout initialized successfully.")

def is_already_posted(file_path):
    """
    Checks our records to see if a specific photo has already been processed.
    Returns True if it's in the DB, False if it's completely new.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Run a classic SELECT statement with a placeholder variable (?)
    cursor.execute(
        "SELECT 1 FROM posted_media WHERE file_path = ?;", 
        (str(file_path),)
    )
    row = cursor.fetchone()
    
    conn.close()
    return row is not None  # Returns True if a record was found

def mark_as_posted(file_path):
    """
    Saves a newly posted file path into our database log.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO posted_media (file_path) VALUES (?);", 
            (str(file_path),)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # This catches it if the path is somehow already marked unique
        pass
    finally:
        conn.close()
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

# Load the .env file located beside this module, regardless of the current folder.
load_dotenv(Path(__file__).with_name(".env"))

DB_URL = (
    f"dbname={os.getenv('DB_NAME')} "
    f"user={os.getenv('DB_USER')} "
    f"password={os.getenv('DB_PASSWORD')} "
    f"host={os.getenv('DB_HOST')} "
    f"port={os.getenv('DB_PORT')}"
)

def get_db_connection():
    """Yields a fresh dictionary-based database connection."""
    # dict_row ensures your results look like {"id": 1, "title": "..."} 
    # instead of just (1, "...")
    return psycopg.connect(DB_URL, row_factory=dict_row)


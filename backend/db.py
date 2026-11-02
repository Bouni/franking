"""SQLite database for the stock and the settings, next to the labels
(persistent volume)"""

import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

LABEL_PATH = os.getenv("LABEL_PATH", default="/opt/docker/invio/labels")

# An empty FRANKING_DB (as in .env.example) means the default
DB_PATH = Path(os.getenv("FRANKING_DB") or os.path.join(LABEL_PATH, "franking.db"))

# The database used to be stock.db, it only held the stock back then
LEGACY_DB_PATH = Path(LABEL_PATH, "stock.db")


def migrate():
    """Rename the old stock.db. Called on startup and not on import, logging
    before main.py configured it would hide all info messages"""
    if LEGACY_DB_PATH.is_file() and not DB_PATH.exists():
        LEGACY_DB_PATH.rename(DB_PATH)
        logging.info(f"Renamed {LEGACY_DB_PATH} to {DB_PATH}")


@contextmanager
def connect(schema: str):
    """Connection with one transaction: committed at the end, rolled back on
    an exception. The tables of the schema are created if missing"""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(schema)
        with con:
            yield con
    finally:
        con.close()

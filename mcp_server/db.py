import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"


def get_connection() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def ensure_agent_tables(con: sqlite3.Connection) -> None:
    """Create the two small tables agents write to (working copy only).

    The original shop tables are not changed. These just hold payment
    proposals waiting for a human and customer message drafts.
    """
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS payment_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,          -- invoice | rent | purchase_order
            ref_id INTEGER NOT NULL,     -- invoice id, lease id, or vendor id
            amount REAL NOT NULL,
            account TEXT NOT NULL,
            reason TEXT,
            ticket_id INTEGER,
            status TEXT NOT NULL DEFAULT 'pending_approval',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS customer_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL
        );
        """
    )

"""SQLite database schema and query helpers."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS user_profile (
    username TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attributes (
    name TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    group_name TEXT NOT NULL,
    group_label TEXT NOT NULL,
    group_priority INTEGER NOT NULL,
    priority INTEGER NOT NULL,
    value_type INTEGER NOT NULL,
    value_type_description TEXT NOT NULL,
    service_name TEXT,
    service_label TEXT,
    manual INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    template TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attribute_values (
    attribute_name TEXT NOT NULL,
    date TEXT NOT NULL,
    value TEXT,
    PRIMARY KEY (attribute_name, date),
    FOREIGN KEY (attribute_name) REFERENCES attributes(name)
);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    sync_type TEXT NOT NULL,
    attributes_synced INTEGER NOT NULL DEFAULT 0,
    values_synced INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    error_message TEXT
);
"""


def connect(db_path):
    """Open a connection to the SQLite database."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn):
    """Create tables if they don't exist."""
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_profile(conn, profile):
    """Insert or replace user profile."""
    conn.execute(
        "INSERT OR REPLACE INTO user_profile (username, data, updated_at) VALUES (?, ?, ?)",
        (profile["username"], json.dumps(profile), datetime.now(UTC).isoformat()),
    )
    conn.commit()


def upsert_attribute(conn, attr):
    """Insert or replace a single attribute metadata row."""
    conn.execute(
        """INSERT OR REPLACE INTO attributes
        (name, label, group_name, group_label, group_priority, priority,
         value_type, value_type_description, service_name, service_label,
         manual, active, template, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            attr["attribute"],
            attr["label"],
            attr["group"]["name"],
            attr["group"]["label"],
            attr["group"]["priority"],
            attr["priority"],
            attr["value_type"],
            attr["value_type_description"],
            attr.get("service", {}).get("name") if attr.get("service") else None,
            attr.get("service", {}).get("label") if attr.get("service") else None,
            int(attr.get("manual", False)),
            int(attr.get("active", True)),
            attr.get("template"),
            datetime.now(UTC).isoformat(),
        ),
    )
    conn.commit()


def upsert_values(conn, attribute_name, values):
    """Bulk insert or replace attribute values.

    values: list of dicts with 'date' and 'value' keys.
    Returns count of rows upserted.
    """
    rows = [(attribute_name, v["date"], v["value"]) for v in values]
    conn.executemany(
        "INSERT OR REPLACE INTO attribute_values (attribute_name, date, value) VALUES (?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def get_last_sync_date(conn, attribute_name):
    """Get the most recent date we have stored for an attribute."""
    row = conn.execute(
        "SELECT MAX(date) as max_date FROM attribute_values WHERE attribute_name = ?",
        (attribute_name,),
    ).fetchone()
    return row["max_date"] if row and row["max_date"] else None


def get_global_last_sync(conn):
    """Get the timestamp of the last successful sync."""
    row = conn.execute(
        "SELECT timestamp FROM sync_log WHERE status IN ('success', 'partial') ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row["timestamp"] if row else None


def get_profile(conn):
    """Load the stored user profile, or None."""
    row = conn.execute("SELECT data FROM user_profile LIMIT 1").fetchone()
    return json.loads(row["data"]) if row else None


def write_sync_log(conn, sync_type, attributes_synced, values_synced, status, error_message=None):
    """Record a sync run in the log."""
    conn.execute(
        """INSERT INTO sync_log (timestamp, sync_type, attributes_synced, values_synced, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (datetime.now(UTC).isoformat(), sync_type, attributes_synced, values_synced, status, error_message),
    )
    conn.commit()


def get_all_attributes(conn):
    """Get all attribute metadata rows, ordered by group then priority."""
    return conn.execute(
        "SELECT * FROM attributes ORDER BY group_priority, priority"
    ).fetchall()


def get_values_for_date(conn, date_str):
    """Get all attribute values for a specific date."""
    return conn.execute(
        "SELECT attribute_name, value FROM attribute_values WHERE date = ?",
        (date_str,),
    ).fetchall()


def get_values_for_date_range(conn, date_from, date_to):
    """Get all attribute values in a date range."""
    return conn.execute(
        "SELECT attribute_name, date, value FROM attribute_values WHERE date >= ? AND date <= ? ORDER BY date",
        (date_from, date_to),
    ).fetchall()


def get_sync_status(conn):
    """Get summary stats for the status command."""
    stats = {}
    row = conn.execute("SELECT COUNT(*) as cnt FROM attributes").fetchone()
    stats["total_attributes"] = row["cnt"]
    row = conn.execute("SELECT COUNT(*) as cnt FROM attribute_values").fetchone()
    stats["total_values"] = row["cnt"]
    row = conn.execute("SELECT MIN(date) as min_d, MAX(date) as max_d FROM attribute_values").fetchone()
    stats["date_min"] = row["min_d"]
    stats["date_max"] = row["max_d"]
    stats["last_sync"] = get_global_last_sync(conn)
    return stats

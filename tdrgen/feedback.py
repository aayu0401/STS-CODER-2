from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .engine import normalize_command

RESULTS = ("verified", "rejected", "needs_review")
REQUIRED_FOR_VERIFIED = ("actual_response", "reviewer", "system_name", "ztpf_release", "environment")
COLUMNS = (
    "command", "expected_response", "actual_response", "result", "system_name",
    "ztpf_release", "environment", "source_file", "reviewer", "notes",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS response_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT NOT NULL,
    expected_response TEXT NOT NULL,
    actual_response TEXT,
    result TEXT NOT NULL CHECK (result IN ('verified', 'rejected', 'needs_review')),
    system_name TEXT,
    ztpf_release TEXT,
    environment TEXT,
    source_file TEXT,
    reviewer TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_feedback_command ON response_feedback (command);
"""


def _connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def record_feedback(db_path: str | Path, item: dict[str, Any]) -> int:
    record = {column: _clean(item.get(column)) for column in COLUMNS}

    missing = [name for name in ("command", "expected_response", "result") if not record[name]]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    if record["result"] not in RESULTS:
        raise ValueError(f"result must be one of: {', '.join(RESULTS)}")
    if record["result"] == "verified":
        missing = [name for name in REQUIRED_FOR_VERIFIED if not record[name]]
        if missing:
            raise ValueError(f"A verified record also needs: {', '.join(missing)}")

    record["command"] = normalize_command(record["command"])
    placeholders = ", ".join("?" for _ in COLUMNS)
    with closing(_connect(db_path)) as connection, connection:
        cursor = connection.execute(
            f"INSERT INTO response_feedback ({', '.join(COLUMNS)}) VALUES ({placeholders})",
            tuple(record[column] for column in COLUMNS),
        )
        return int(cursor.lastrowid)


def feedback_for_command(db_path: str | Path, command: str, limit: int = 20) -> list[dict[str, Any]]:
    with closing(_connect(db_path)) as connection:
        rows = connection.execute(
            "SELECT * FROM response_feedback WHERE command = ? ORDER BY id DESC LIMIT ?",
            (normalize_command(command), limit),
        ).fetchall()
    return [dict(row) for row in rows]


def recent_feedback(db_path: str | Path, limit: int = 20) -> list[dict[str, Any]]:
    with closing(_connect(db_path)) as connection:
        rows = connection.execute(
            "SELECT * FROM response_feedback ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]

"""Append-only, hash-chained log stored in SQLite."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from . import crypto
from .models import EntryStatus, FailReason, VerifyResult

# An entry as stored: plain dict so a tampered row can never crash loading.
RawEntry = dict[str, Any]

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    idx INTEGER PRIMARY KEY,
    reading_json TEXT NOT NULL,
    signature TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL
)
"""


class Ledger:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _row(r: sqlite3.Row) -> RawEntry:
        return {
            "index": r["idx"],
            "reading": json.loads(r["reading_json"]),
            "signature": r["signature"],
            "prev_hash": r["prev_hash"],
            "entry_hash": r["entry_hash"],
        }

    def count(self) -> int:
        with self._conn() as c:
            return int(c.execute("SELECT COUNT(*) FROM entries").fetchone()[0])

    def all_entries(self) -> list[RawEntry]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM entries ORDER BY idx").fetchall()
        return [self._row(r) for r in rows]

    def get(self, idx: int) -> RawEntry | None:
        with self._conn() as c:
            r = c.execute("SELECT * FROM entries WHERE idx = ?", (idx,)).fetchone()
        return self._row(r) if r else None

    def append(self, reading: dict[str, Any], signature: str) -> RawEntry:
        """Add one signed reading to the end of the chain."""
        reading = crypto.round_reading(reading)
        with self._conn() as c:
            last = c.execute(
                "SELECT idx, entry_hash FROM entries ORDER BY idx DESC LIMIT 1"
            ).fetchone()
            idx = 0 if last is None else last["idx"] + 1
            prev = crypto.GENESIS_PREV if last is None else last["entry_hash"]
            entry_hash = crypto.compute_entry_hash(prev, reading, signature)
            c.execute(
                "INSERT INTO entries VALUES (?, ?, ?, ?, ?)",
                (idx, json.dumps(reading, sort_keys=True), signature, prev, entry_hash),
            )
        return {
            "index": idx,
            "reading": reading,
            "signature": signature,
            "prev_hash": prev,
            "entry_hash": entry_hash,
        }

    def clear(self) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM entries")

    # ---- demo-only helpers (the API gates these behind DEMO_MODE) ----
    def tamper(self, idx: int, field: str, value: Any) -> tuple[Any, Any]:
        """Edit a stored reading WITHOUT re-signing. Returns (old, new)."""
        entry = self.get(idx)
        if entry is None:
            raise KeyError(f"no entry {idx}")
        if field not in entry["reading"]:
            raise KeyError(f"no field {field}")
        old = entry["reading"][field]
        entry["reading"][field] = value
        with self._conn() as c:
            c.execute(
                "UPDATE entries SET reading_json = ? WHERE idx = ?",
                (json.dumps(entry["reading"], sort_keys=True), idx),
            )
        return old, value

    def delete_entry(self, idx: int) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM entries WHERE idx = ?", (idx,))


def check_entry(
    entry: RawEntry, expected_prev: str, registry: dict[str, str]
) -> tuple[FailReason | None, bool, bool, bool]:
    """Check one entry on its own.

    Returns (first_failure_reason, signature_ok, prev_link_ok, entry_hash_ok).
    Order of reasons: unknown_probe, malformed_reading, bad_signature,
    prev_hash_mismatch, entry_hash_mismatch.
    """
    reading = entry["reading"]
    pub = registry.get(reading.get("probe_id", "")) if isinstance(reading, dict) else None
    try:
        sig_ok = pub is not None and crypto.verify_sig(pub, reading, entry["signature"])
        prev_ok = entry["prev_hash"] == expected_prev
        hash_ok = entry["entry_hash"] == crypto.compute_entry_hash(
            entry["prev_hash"], reading, entry["signature"]
        )
    except (ValueError, TypeError, KeyError):
        return "malformed_reading", False, False, False

    reason: FailReason | None = None
    if pub is None:
        reason = "unknown_probe"
    elif not sig_ok:
        reason = "bad_signature"
    elif not prev_ok:
        reason = "prev_hash_mismatch"
    elif not hash_ok:
        reason = "entry_hash_mismatch"
    return reason, sig_ok, prev_ok, hash_ok


def verify_chain(
    entries: list[RawEntry], registry: dict[str, str]
) -> tuple[VerifyResult, dict[int, EntryStatus]]:
    """Walk the chain. Report the FIRST failing index and why.

    Entries after the first failure cannot be trusted either, because the chain
    no longer proves they were stored in this order. They get
    'untrusted_after_break'.
    """
    statuses: dict[int, EntryStatus] = {}
    first_bad: int | None = None
    reason: FailReason | None = None
    checked = 0
    prev = crypto.GENESIS_PREV
    for e in entries:
        if first_bad is not None:
            statuses[e["index"]] = "untrusted_after_break"
            continue
        checked += 1
        fail, _, _, _ = check_entry(e, prev, registry)
        if fail is not None:
            first_bad, reason = e["index"], fail
            statuses[e["index"]] = "tampered"
        else:
            statuses[e["index"]] = "verified"
        prev = e["entry_hash"]
    total = len(entries)
    result = VerifyResult(
        ok=first_bad is None,
        total=total,
        checked=checked,
        first_bad_index=first_bad,
        reason=reason,
        untrusted_count=sum(1 for s in statuses.values() if s == "untrusted_after_break"),
    )
    return result, statuses

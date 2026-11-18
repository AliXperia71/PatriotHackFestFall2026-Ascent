"""Pydantic schemas (API boundary and data contracts)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Reading(BaseModel):
    probe_id: str
    zone_id: str
    ts: str
    pm25_ugm3: float
    o2_pct: float
    co_ppm: float
    radiation_usv_h: float
    temp_c: float
    machine_contacts: int


class LedgerEntry(BaseModel):
    index: int
    reading: Reading
    signature: str
    prev_hash: str
    entry_hash: str


EntryStatus = Literal["verified", "tampered", "untrusted_after_break"]
FailReason = Literal[
    "unknown_probe",
    "malformed_reading",
    "bad_signature",
    "prev_hash_mismatch",
    "entry_hash_mismatch",
]


class ReadingOut(LedgerEntry):
    status: EntryStatus


class VerifyResult(BaseModel):
    ok: bool
    total: int
    checked: int
    first_bad_index: int | None = None
    reason: FailReason | None = None
    untrusted_count: int = 0


class EntryCheck(BaseModel):
    """Result of the per-reading 'Verify' click."""

    index: int
    signature_valid: bool
    prev_link_valid: bool
    entry_hash_valid: bool
    status: EntryStatus
    chain_intact: bool
    first_bad_index: int | None = None
    message: str


class TamperRequest(BaseModel):
    index: int | None = Field(default=None, description="Entry to edit. Default: a fixed demo entry.")
    field: str = "pm25_ugm3"
    value: Any = 1.0


class TamperResult(BaseModel):
    index: int
    field: str
    old_value: Any
    new_value: Any


class ZoneOut(BaseModel):
    zone_id: str
    name: str
    lat: float
    lon: float
    status: EntryStatus
    latest: ReadingOut | None

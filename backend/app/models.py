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


# ---------------- Forecast ----------------
class BandPoint(BaseModel):
    day: int
    mid: float
    lo: float
    hi: float


class SeriesForecast(BaseModel):
    metric: Literal["pm25_ugm3", "radiation_usv_h"]
    threshold: float
    observed: list[tuple[int, float]]  # (day, daily mean)
    projected: list[BandPoint]
    fit: dict[str, float]              # y = c + a * exp(-k * day)
    current: float                     # latest observed daily mean
    cross_day: int | None              # first day the fit is at/below threshold
    cross_lo: int | None
    cross_hi: int | None


class ZoneForecast(BaseModel):
    zone_id: str
    name: str
    ok: bool
    message: str
    days_used: int
    last_day: int
    pm25: SeriesForecast | None = None
    radiation: SeriesForecast | None = None
    safe_day: int | None = None
    safe_day_lo: int | None = None
    safe_day_hi: int | None = None
    safe_date: str | None = None


class ForecastSummary(BaseModel):
    zones: list[ZoneForecast]
    first_safe_zone: str | None
    ranking: list[str]   # zone ids, soonest safe first
    note: str


# ---------------- Pilot ----------------
class OptionScore(BaseModel):
    option: str
    total: float
    viable: bool
    contributions: dict[str, float]   # weight * normalized value
    normalized: dict[str, float]
    raw: dict[str, float]


class ZoneOptions(BaseModel):
    zone_id: str
    recommended: str | None
    options: list[OptionScore]
    weights: dict[str, float]
    note: str


class Candidate(BaseModel):
    person_id: str
    age: int
    health: float
    skill: str
    level: int
    years_below: int
    volunteer: bool


class ChosenPerson(BaseModel):
    person: Candidate
    score: float
    contributions: dict[str, float]


class GroupResult(BaseModel):
    selected: list[ChosenPerson]
    pool_size: int
    eligible: int
    excluded: dict[str, int]   # reason -> count
    band_size: int
    band_cutoff: float
    weights: dict[str, float]
    seed: int
    method: str


# ---------------- Migrate ----------------
class WaveRow(BaseModel):
    wave: int
    day: int
    date: str
    level: int
    destination: str
    population: int


class MigratePlan(BaseModel):
    rows: list[WaveRow]
    zone_open_wave: dict[str, int | None]
    placed: int
    unplaced: dict[int, int]
    total_population: int
    wave_totals: dict[int, int]
    limits: dict[str, int]
    method: str

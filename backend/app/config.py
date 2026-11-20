"""Settings for Ascent. Thresholds and weights live here.

All safety thresholds are ILLUSTRATIVE. They are not medical advice.
"""
from __future__ import annotations

import os
from pathlib import Path

SEED: int = 2087

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH: Path = Path(os.environ.get("ASCENT_DB", REPO_ROOT / "data" / "ledger.db"))


def demo_mode() -> bool:
    """True when DEMO_MODE=1. Read at call time so tests can change it."""
    return os.environ.get("DEMO_MODE", "0") == "1"


# Fixed decimal places per numeric field. Applied BEFORE signing and hashing.
PRECISION: dict[str, int] = {
    "pm25_ugm3": 2,
    "o2_pct": 2,
    "co_ppm": 2,
    "radiation_usv_h": 3,
    "temp_c": 2,
}
INT_FIELDS: tuple[str, ...] = ("machine_contacts",)

# Illustrative "safe" thresholds (a reading at or below these is safe).
SAFE_PM25_UGM3: float = 12.0
SAFE_RADIATION_USV_H: float = 0.30
SAFE_CO_PPM: float = 9.0
SAFE_O2_PCT_MIN: float = 19.5

# Synthetic data size.
DAYS: int = 60
READINGS_PER_DAY: int = 4
START_TS = "2087-01-14T00:00:00Z"

# Zones: id -> (name, lat, lon). Coordinates are fictional-ish map points.
ZONES: dict[str, tuple[str, float, float]] = {
    "Z-NORTH-3": ("North Ridge", 38.90, -77.30),
    "Z-NORTH-1": ("North Basin", 38.86, -77.26),
    "Z-EAST-2": ("East Flats", 38.83, -77.15),
    "Z-SOUTH-1": ("South Valley", 38.74, -77.28),
    "Z-WEST-2": ("West Hills", 38.82, -77.42),
    "Z-CENTRAL-1": ("Central Plain", 38.82, -77.29),
}
PROBES_PER_ZONE: int = 2

# Per zone recovery shape: (pm25_start, pm25_k_per_day, rad_start, rad_k_per_day)
# Floors are the "healed" background level. Different speeds so the forecast is interesting.
ZONE_DECAY: dict[str, tuple[float, float, float, float]] = {
    "Z-NORTH-3": (60.0, 0.055, 0.90, 0.040),
    "Z-NORTH-1": (85.0, 0.035, 1.10, 0.030),
    "Z-EAST-2": (110.0, 0.028, 1.40, 0.022),
    "Z-SOUTH-1": (70.0, 0.045, 0.80, 0.050),
    "Z-WEST-2": (95.0, 0.020, 1.20, 0.018),
    "Z-CENTRAL-1": (140.0, 0.015, 1.80, 0.012),
}
PM25_FLOOR: float = 4.0
RAD_FLOOR: float = 0.12

# ---------------- Forecast ----------------
FORECAST_HORIZON_DAYS: int = 365   # project this far from the first reading
FORECAST_SAMPLES: int = 400        # parameter draws for the uncertainty band
FORECAST_MIN_DAYS: int = 5         # fewer verified days than this -> no forecast
BAND_LO_PCT: float = 5.0
BAND_HI_PCT: float = 95.0

# ---------------- Pilot (all numbers illustrative) ----------------
# protection = share of outside pollution the option blocks.
OPTIONS: dict[str, dict[str, float]] = {
    "suit": {"cost": 1.0, "capacity": 50, "deploy_days": 7, "protection": 0.80},
    "dome": {"cost": 4.0, "capacity": 500, "deploy_days": 60, "protection": 0.85},
    "outpost": {"cost": 10.0, "capacity": 2000, "deploy_days": 120, "protection": 0.99},
}
OPTION_WEIGHTS: dict[str, float] = {
    "safety": 0.45, "cost": 0.20, "capacity": 0.20, "time": 0.15,
}
MIN_SAFETY_MARGIN: float = 0.20  # below this an option is "not viable"

CANDIDATES: int = 300
GROUP_SIZE: int = 20
TOP_BAND_FACTOR: int = 2          # lottery among the top GROUP_SIZE * this
NEEDED_SKILLS: tuple[str, ...] = ("engineer", "medic", "builder")
ALL_SKILLS: tuple[str, ...] = ("engineer", "medic", "builder", "farmer", "scientist", "teacher")
ELIG_MIN_AGE: int = 18
ELIG_MAX_AGE: int = 60
ELIG_MIN_HEALTH: float = 0.60
GROUP_WEIGHTS: dict[str, float] = {
    "health": 0.30, "skill": 0.30, "depth": 0.25, "years_below": 0.15,
}

# ---------------- Migrate (thin, greedy) ----------------
HOLLOW_LEVELS: int = 8
# People per level (demo district). Level 8 is the deepest.
LEVEL_POPULATION: dict[int, int] = {
    1: 9000, 2: 10000, 3: 11000, 4: 12000, 5: 13000, 6: 14000, 7: 15000, 8: 16000,
}
WAVES: int = 12
WAVE_DAYS: int = 30
SUPPLY_PER_WAVE: int = 12000       # people we can feed/move per wave, total
ZONE_INTAKE_PER_WAVE: int = 5000   # people one zone can take in per wave
ZONE_CAPACITY: int = 25000         # total people one zone can hold

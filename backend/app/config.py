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

"""Synthetic probes and surface data. Seeded, so demos repeat exactly."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from . import config, crypto
from .ledger import Ledger


def probe_ids() -> dict[str, list[str]]:
    """zone_id -> its probe ids, e.g. Z-NORTH-3 -> [P-01, P-02]."""
    out: dict[str, list[str]] = {}
    n = 1
    for zone in config.ZONES:
        out[zone] = []
        for _ in range(config.PROBES_PER_ZONE):
            out[zone].append(f"P-{n:02d}")
            n += 1
    return out


def probe_zone() -> dict[str, str]:
    return {p: z for z, ps in probe_ids().items() for p in ps}


def public_registry() -> dict[str, str]:
    """Public keys only. This is what a verifier is allowed to know."""
    return {
        p: crypto.public_key_hex(crypto.probe_private_key(p))
        for ps in probe_ids().values()
        for p in ps
    }


def generate_readings(rng: np.random.Generator) -> list[dict[str, Any]]:
    """All readings in time order (one tick = every probe reports once)."""
    start = datetime.strptime(config.START_TS, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    step = timedelta(hours=24 / config.READINGS_PER_DAY)
    ticks = config.DAYS * config.READINGS_PER_DAY
    pz = probe_zone()
    out: list[dict[str, Any]] = []
    for t in range(ticks):
        ts = (start + step * t).strftime("%Y-%m-%dT%H:%M:%SZ")
        day = t / config.READINGS_PER_DAY
        for probe, zone in pz.items():
            p0, pk, r0, rk = config.ZONE_DECAY[zone]
            pm = config.PM25_FLOOR + (p0 - config.PM25_FLOOR) * np.exp(-pk * day)
            rad = config.RAD_FLOOR + (r0 - config.RAD_FLOOR) * np.exp(-rk * day)
            out.append(
                {
                    "probe_id": probe,
                    "zone_id": zone,
                    "ts": ts,
                    "pm25_ugm3": max(0.0, float(pm * (1 + rng.normal(0, 0.03)))),
                    "o2_pct": float(20.7 + rng.normal(0, 0.15)),
                    "co_ppm": max(0.0, float(1.0 + rng.normal(0, 0.2))),
                    "radiation_usv_h": max(0.0, float(rad * (1 + rng.normal(0, 0.03)))),
                    "temp_c": float(14.0 + 3 * np.sin(2 * np.pi * (t % config.READINGS_PER_DAY)
                                                      / config.READINGS_PER_DAY)
                                    + rng.normal(0, 0.4)),
                    "machine_contacts": int(rng.poisson(0.15)),
                }
            )
    return out


def generate_ledger(ledger: Ledger) -> int:
    """Fill an empty ledger with signed readings. Returns how many were added."""
    rng = np.random.default_rng(config.SEED)
    keys: dict[str, Ed25519PrivateKey] = {
        p: crypto.probe_private_key(p) for p in public_registry()
    }
    readings = generate_readings(rng)
    for r in readings:
        r = crypto.round_reading(r)
        ledger.append(r, crypto.sign(keys[r["probe_id"]], r))
    return len(readings)

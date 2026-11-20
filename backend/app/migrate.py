"""Migrate: thin greedy wave planner.

A zone opens in the first wave that starts after its CONSERVATIVE safe day
(upper end of the forecast interval). Deep levels go first. Caps: total
supply per wave, intake per zone per wave, total capacity per zone.
"""
from __future__ import annotations

from . import config
from .forecast import date_of
from .models import ForecastSummary, MigratePlan, WaveRow


def open_wave(safe_day_hi: int | None, first_day: int) -> int | None:
    if safe_day_hi is None:
        return None
    for w in range(1, config.WAVES + 1):
        if first_day + (w - 1) * config.WAVE_DAYS >= safe_day_hi:
            return w
    return None


def plan(fc: ForecastSummary) -> MigratePlan:
    ok_zones = [z for z in fc.zones if z.ok]
    first_day = (max(z.last_day for z in ok_zones) + 1) if ok_zones else 0
    opens: dict[str, int | None] = {
        z.zone_id: open_wave(z.safe_day_hi if z.ok else None, first_day) for z in fc.zones
    }
    remaining = dict(config.LEVEL_POPULATION)
    capacity = {z: config.ZONE_CAPACITY for z in opens}
    rows: list[WaveRow] = []
    wave_totals: dict[int, int] = {}
    for w in range(1, config.WAVES + 1):
        day = first_day + (w - 1) * config.WAVE_DAYS
        supply = config.SUPPLY_PER_WAVE
        intake = {z: config.ZONE_INTAKE_PER_WAVE for z, ow in opens.items() if ow is not None and ow <= w}
        for level in sorted(remaining, reverse=True):          # deepest first
            for zone in sorted(intake, key=lambda z: (-capacity[z], z)):
                take = min(remaining[level], intake[zone], capacity[zone], supply)
                if take <= 0:
                    continue
                rows.append(WaveRow(wave=w, day=day, date=date_of(day), level=level,
                                    destination=zone, population=take))
                remaining[level] -= take
                intake[zone] -= take
                capacity[zone] -= take
                supply -= take
        wave_totals[w] = config.SUPPLY_PER_WAVE - supply
    placed = sum(r.population for r in rows)
    return MigratePlan(
        rows=rows, zone_open_wave=opens, placed=placed,
        unplaced={lv: n for lv, n in remaining.items() if n > 0},
        total_population=sum(config.LEVEL_POPULATION.values()),
        wave_totals=wave_totals,
        limits={"supply_per_wave": config.SUPPLY_PER_WAVE,
                "zone_intake_per_wave": config.ZONE_INTAKE_PER_WAVE,
                "zone_capacity": config.ZONE_CAPACITY,
                "wave_days": config.WAVE_DAYS, "waves": config.WAVES},
        method="Greedy: deepest level first, into open zones, within all caps.",
    )

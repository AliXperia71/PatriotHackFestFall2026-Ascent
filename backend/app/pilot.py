"""Pilot: score reinhabitation options per zone, then pick a fair first group.

No black box: every score is a sum of (weight * normalized criterion), and we
return each part.
"""
from __future__ import annotations

import numpy as np

from . import config
from .models import Candidate, ChosenPerson, GroupResult, OptionScore, ZoneForecast, ZoneOptions


def _norm_low_is_good(v: float, values: list[float]) -> float:
    lo, hi = min(values), max(values)
    return 1.0 if hi == lo else (hi - v) / (hi - lo)


def _norm_high_is_good(v: float, values: list[float]) -> float:
    lo, hi = min(values), max(values)
    return 1.0 if hi == lo else (v - lo) / (hi - lo)


def safety_margin(protection: float, pm25_now: float, rad_now: float) -> float:
    """1 = exposure far under threshold, 0 = at or over it. Worst pollutant counts."""
    margins = [
        1.0 - pm25_now * (1 - protection) / config.SAFE_PM25_UGM3,
        1.0 - rad_now * (1 - protection) / config.SAFE_RADIATION_USV_H,
    ]
    return float(np.clip(min(margins), 0.0, 1.0))


def score_options(zf: ZoneForecast) -> ZoneOptions:
    note = "Weights and option numbers are illustrative."
    if not zf.ok or zf.pm25 is None or zf.radiation is None:
        return ZoneOptions(zone_id=zf.zone_id, recommended=None, options=[],
                           weights=config.OPTION_WEIGHTS, note=f"No forecast: {zf.message}")
    pm_now, rad_now = zf.pm25.current, zf.radiation.current
    opts = config.OPTIONS
    costs = [o["cost"] for o in opts.values()]
    caps = [o["capacity"] for o in opts.values()]
    deploys = [o["deploy_days"] for o in opts.values()]
    scored: list[OptionScore] = []
    for name, o in opts.items():
        normalized = {
            "safety": round(safety_margin(o["protection"], pm_now, rad_now), 4),
            "cost": round(_norm_low_is_good(o["cost"], costs), 4),
            "capacity": round(_norm_high_is_good(o["capacity"], caps), 4),
            "time": round(_norm_low_is_good(o["deploy_days"], deploys), 4),
        }
        contrib = {k: round(config.OPTION_WEIGHTS[k] * v, 4) for k, v in normalized.items()}
        scored.append(OptionScore(
            option=name, total=round(sum(contrib.values()), 4),
            viable=normalized["safety"] >= config.MIN_SAFETY_MARGIN,
            contributions=contrib, normalized=normalized,
            raw={**o, "pm25_now": pm_now, "radiation_now": rad_now},
        ))
    viable = [s for s in scored if s.viable]
    best = max(viable, key=lambda s: s.total).option if viable else None
    return ZoneOptions(zone_id=zf.zone_id, recommended=best,
                       options=sorted(scored, key=lambda s: -s.total),
                       weights=config.OPTION_WEIGHTS, note=note)


def candidate_pool(n: int = config.CANDIDATES, seed: int = config.SEED) -> list[Candidate]:
    rng = np.random.default_rng([seed, 7])
    pool: list[Candidate] = []
    for i in range(n):
        pool.append(Candidate(
            person_id=f"R-{i + 1:03d}",
            age=int(rng.integers(14, 76)),
            health=round(float(rng.beta(5, 2)), 3),
            skill=str(rng.choice(config.ALL_SKILLS)),
            level=int(rng.integers(1, config.HOLLOW_LEVELS + 1)),
            years_below=int(rng.integers(1, 41)),
            volunteer=bool(rng.random() < 0.7),
        ))
    return pool


def exclusion_reason(p: Candidate) -> str | None:
    if not p.volunteer:
        return "did_not_volunteer"
    if p.age < config.ELIG_MIN_AGE:
        return "under_min_age"
    if p.age > config.ELIG_MAX_AGE:
        return "over_max_age"
    if p.health < config.ELIG_MIN_HEALTH:
        return "health_below_min"
    return None


def person_contributions(p: Candidate) -> dict[str, float]:
    w = config.GROUP_WEIGHTS
    normalized = {
        "health": p.health,
        "skill": 1.0 if p.skill in config.NEEDED_SKILLS else 0.0,
        "depth": p.level / config.HOLLOW_LEVELS,        # deep levels suffer most
        "years_below": min(p.years_below / 40, 1.0),
    }
    return {k: round(w[k] * v, 4) for k, v in normalized.items()}


def select_group(size: int = config.GROUP_SIZE, seed: int = config.SEED) -> GroupResult:
    pool = candidate_pool(seed=seed)
    excluded: dict[str, int] = {}
    eligible: list[ChosenPerson] = []
    for p in pool:
        reason = exclusion_reason(p)
        if reason:
            excluded[reason] = excluded.get(reason, 0) + 1
            continue
        c = person_contributions(p)
        eligible.append(ChosenPerson(person=p, score=round(sum(c.values()), 4), contributions=c))
    eligible.sort(key=lambda c: (-c.score, c.person.person_id))
    band = eligible[: size * config.TOP_BAND_FACTOR]
    rng = np.random.default_rng([seed, 11])
    k = min(size, len(band))
    picks = sorted(rng.choice(len(band), size=k, replace=False).tolist()) if k else []
    chosen = sorted((band[i] for i in picks), key=lambda c: -c.score)
    return GroupResult(
        selected=chosen, pool_size=len(pool), eligible=len(eligible), excluded=excluded,
        band_size=len(band), band_cutoff=band[-1].score if band else 0.0,
        weights=config.GROUP_WEIGHTS, seed=seed,
        method=(f"Eligibility filter, then weighted score, then a seeded lottery "
                f"picks {size} from the top {len(band)}."),
    )

"""Recovery forecast: fit exponential decay to VERIFIED readings only."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

import numpy as np
from scipy.optimize import curve_fit

from . import config
from .ledger import RawEntry
from .models import BandPoint, EntryStatus, ForecastSummary, SeriesForecast, ZoneForecast

_START = datetime.strptime(config.START_TS, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
_METRICS = {
    "pm25_ugm3": config.SAFE_PM25_UGM3,
    "radiation_usv_h": config.SAFE_RADIATION_USV_H,
}


def day_of(ts: str) -> int:
    t = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (t - _START).days


def date_of(day: int) -> str:
    return (_START + timedelta(days=day)).strftime("%Y-%m-%d")


def decay(t: np.ndarray, a: float, k: float, c: float) -> np.ndarray:
    return c + a * np.exp(-k * t)


def daily_means(entries: list[RawEntry], statuses: dict[int, EntryStatus]) -> dict[str, dict[str, list[tuple[int, float]]]]:
    """zone -> metric -> [(day, mean)] using only verified entries."""
    sums: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for e in entries:
        if statuses.get(e["index"]) != "verified":
            continue
        r = e["reading"]
        d = day_of(r["ts"])
        for m in _METRICS:
            sums[(r["zone_id"], m, d)].append(float(r[m]))
    out: dict[str, dict[str, list[tuple[int, float]]]] = defaultdict(lambda: defaultdict(list))
    for (z, m, d), vals in sorted(sums.items()):
        out[z][m].append((d, round(float(np.mean(vals)), 4)))
    return out


def _first_cross(curve: np.ndarray, days: np.ndarray, threshold: float) -> int | None:
    below = np.nonzero(curve <= threshold)[0]
    return int(days[below[0]]) if below.size else None


def fit_series(metric: str, series: list[tuple[int, float]], rng: np.random.Generator) -> tuple[SeriesForecast, np.ndarray]:
    """Fit one pollutant. Returns the forecast and per-sample crossing days (nan = never)."""
    threshold = _METRICS[metric]
    t = np.array([d for d, _ in series], dtype=float)
    y = np.array([v for _, v in series], dtype=float)
    p0 = (max(y[0] - y.min(), 1e-3), 0.03, max(y.min() * 0.8, 0.0))
    popt, pcov = curve_fit(
        decay, t, y, p0=p0, bounds=([0.0, 1e-4, 0.0], [np.inf, 2.0, np.inf]), maxfev=20000
    )
    days = np.arange(0, config.FORECAST_HORIZON_DAYS + 1)
    mid = decay(days, *popt)

    if np.all(np.isfinite(pcov)):
        draws = rng.multivariate_normal(popt, pcov, size=config.FORECAST_SAMPLES)
        draws[:, 0] = np.clip(draws[:, 0], 0, None)
        draws[:, 1] = np.clip(draws[:, 1], 1e-4, None)
        draws[:, 2] = np.clip(draws[:, 2], 0, None)
    else:  # fit too poor for an interval: band collapses to the line
        draws = np.tile(popt, (config.FORECAST_SAMPLES, 1))
    curves = draws[:, 2:3] + draws[:, 0:1] * np.exp(-draws[:, 1:2] * days[None, :])
    lo = np.percentile(curves, config.BAND_LO_PCT, axis=0)
    hi = np.percentile(curves, config.BAND_HI_PCT, axis=0)

    crosses = np.array(
        [c if (c := _first_cross(cv, days, threshold)) is not None else np.nan for cv in curves]
    )
    finite = crosses[np.isfinite(crosses)]
    # Only give an interval when most draws cross; otherwise the date is too unsure.
    enough = finite.size >= 0.9 * crosses.size
    step = 3  # thin the curve for the JSON payload
    sf = SeriesForecast(
        metric=metric,  # type: ignore[arg-type]
        threshold=threshold,
        observed=series,
        projected=[
            BandPoint(day=int(d), mid=round(float(mid[d]), 4), lo=round(float(lo[d]), 4), hi=round(float(hi[d]), 4))
            for d in days[::step]
        ],
        fit={"a": round(float(popt[0]), 5), "k": round(float(popt[1]), 5), "c": round(float(popt[2]), 5)},
        current=series[-1][1],
        cross_day=_first_cross(mid, days, threshold),
        cross_lo=int(np.percentile(finite, config.BAND_LO_PCT)) if enough else None,
        cross_hi=int(np.percentile(finite, config.BAND_HI_PCT)) if enough else None,
    )
    return sf, crosses


def forecast_zone(zone_id: str, per_metric: dict[str, list[tuple[int, float]]]) -> ZoneForecast:
    name = config.ZONES[zone_id][0]
    pm, rad = per_metric.get("pm25_ugm3", []), per_metric.get("radiation_usv_h", [])
    days_used = min(len(pm), len(rad))
    last_day = max([d for d, _ in pm] + [0])
    if days_used < config.FORECAST_MIN_DAYS:
        return ZoneForecast(
            zone_id=zone_id, name=name, ok=False, days_used=days_used, last_day=last_day,
            message=f"Not enough verified data ({days_used} days, need {config.FORECAST_MIN_DAYS}).",
        )
    # Seed per zone so one zone's result does not depend on the others.
    rng = np.random.default_rng([config.SEED, list(config.ZONES).index(zone_id)])
    try:
        pm_f, pm_x = fit_series("pm25_ugm3", pm, rng)
        rad_f, rad_x = fit_series("radiation_usv_h", rad, rng)
    except (RuntimeError, ValueError) as exc:
        return ZoneForecast(
            zone_id=zone_id, name=name, ok=False, days_used=days_used, last_day=last_day,
            message=f"Fit failed: {exc}",
        )
    safe = None if pm_f.cross_day is None or rad_f.cross_day is None else max(pm_f.cross_day, rad_f.cross_day)
    both = np.fmax(pm_x, rad_x)  # a draw is safe when BOTH pollutants are under
    both = np.where(np.isnan(pm_x) | np.isnan(rad_x), np.nan, both)
    finite = both[np.isfinite(both)]
    enough = finite.size >= 0.9 * both.size
    if safe is None:
        msg = f"Not projected safe within {config.FORECAST_HORIZON_DAYS} days."
    elif safe <= last_day:
        msg = f"Already under both thresholds (since about day {safe})."
    else:
        msg = f"Projected safe around {date_of(safe)}."
    return ZoneForecast(
        zone_id=zone_id, name=name, ok=True, message=msg, days_used=days_used, last_day=last_day,
        pm25=pm_f, radiation=rad_f, safe_day=safe,
        safe_day_lo=int(np.percentile(finite, config.BAND_LO_PCT)) if enough else None,
        safe_day_hi=int(np.percentile(finite, config.BAND_HI_PCT)) if enough else None,
        safe_date=date_of(safe) if safe is not None else None,
    )


def forecast_all(entries: list[RawEntry], statuses: dict[int, EntryStatus]) -> ForecastSummary:
    means = daily_means(entries, statuses)
    zones = [forecast_zone(z, means.get(z, {})) for z in config.ZONES]
    ranked = sorted(
        (z for z in zones if z.ok and z.safe_day is not None), key=lambda z: (z.safe_day, z.zone_id)
    )
    return ForecastSummary(
        zones=zones,
        first_safe_zone=ranked[0].zone_id if ranked else None,
        ranking=[z.zone_id for z in ranked],
        note="Uses only verified readings. Thresholds are illustrative, not medical advice.",
    )

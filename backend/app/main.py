"""FastAPI app: Prove (sign, log, verify, tamper)."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import config, forecast, ledger as ledger_mod, migrate, pilot, simulator
from .ledger import Ledger, RawEntry, check_entry
from .models import (
    EntryCheck,
    EntryStatus,
    ForecastSummary,
    GroupResult,
    MigratePlan,
    ZoneForecast,
    ZoneOptions,
    Reading,
    ReadingOut,
    TamperRequest,
    TamperResult,
    VerifyResult,
    ZoneOut,
)
from . import crypto

# Worst status wins for a zone: tampered > untrusted > verified.
_RANK: dict[EntryStatus, int] = {"verified": 0, "untrusted_after_break": 1, "tampered": 2}


def create_app(db_path: Path | str | None = None, demo_mode: bool | None = None) -> FastAPI:
    led = Ledger(db_path or config.DB_PATH)
    registry = simulator.public_registry()
    is_demo = config.demo_mode() if demo_mode is None else demo_mode

    def ensure_data() -> None:
        if led.count() == 0:
            simulator.generate_ledger(led)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        ensure_data()
        yield

    app = FastAPI(title="Ascent", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def out(e: RawEntry, st: dict[int, EntryStatus]) -> ReadingOut:
        return ReadingOut(**e, status=st[e["index"]])

    def snapshot() -> tuple[list[RawEntry], VerifyResult, dict[int, EntryStatus]]:
        entries = led.all_entries()
        result, statuses = ledger_mod.verify_chain(entries, registry)
        return entries, result, statuses

    def require_demo() -> None:
        if not is_demo:
            raise HTTPException(403, "Demo endpoints need DEMO_MODE=1")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "demo_mode": is_demo, "entries": led.count()}

    @app.get("/api/probes")
    def probes() -> dict[str, Any]:
        return {"public_keys": registry, "zones": simulator.probe_ids()}

    @app.get("/api/readings", response_model=list[ReadingOut])
    def readings(zone_id: str | None = None, limit: int = Query(50, ge=1, le=500)):
        entries, _, st = snapshot()
        if zone_id is not None:
            if zone_id not in config.ZONES:
                raise HTTPException(404, f"unknown zone {zone_id}")
            entries = [e for e in entries if e["reading"].get("zone_id") == zone_id]
        return [out(e, st) for e in reversed(entries[-limit:])]  # newest first

    @app.get("/api/zones", response_model=list[ZoneOut])
    def zones():
        entries, _, st = snapshot()
        result: list[ZoneOut] = []
        for zid, (name, lat, lon) in config.ZONES.items():
            zes = [e for e in entries if e["reading"].get("zone_id") == zid]
            worst: EntryStatus = "verified"
            for e in zes:
                if _RANK[st[e["index"]]] > _RANK[worst]:
                    worst = st[e["index"]]
            result.append(
                ZoneOut(
                    zone_id=zid, name=name, lat=lat, lon=lon, status=worst,
                    latest=out(zes[-1], st) if zes else None,
                )
            )
        return result

    @app.get("/api/verify", response_model=VerifyResult)
    def verify():
        return snapshot()[1]

    @app.get("/api/verify/{index}", response_model=EntryCheck)
    def verify_one(index: int):
        entries, result, st = snapshot()
        by_idx = {e["index"]: (i, e) for i, e in enumerate(entries)}
        if index not in by_idx:
            raise HTTPException(404, f"no entry {index}")
        pos, e = by_idx[index]
        prev = entries[pos - 1]["entry_hash"] if pos > 0 else crypto.GENESIS_PREV
        _, sig_ok, prev_ok, hash_ok = check_entry(e, prev, registry)
        status = st[index]
        if status == "verified":
            msg = "Signature valid. Hash chain intact."
        elif status == "tampered":
            msg = "BROKEN: this entry does not match its signature or hash."
        else:
            msg = f"Untrusted: the chain broke earlier, at entry {result.first_bad_index}."
        return EntryCheck(
            index=index, signature_valid=sig_ok, prev_link_valid=prev_ok,
            entry_hash_valid=hash_ok, status=status, chain_intact=result.ok,
            first_bad_index=result.first_bad_index, message=msg,
        )

    def current_forecast() -> ForecastSummary:
        entries, _, st = snapshot()
        return forecast.forecast_all(entries, st)

    def check_zone(zone_id: str | None) -> None:
        if zone_id is not None and zone_id not in config.ZONES:
            raise HTTPException(404, f"unknown zone {zone_id}")

    @app.get("/api/forecast", response_model=ForecastSummary)
    def get_forecast(zone_id: str | None = None):
        check_zone(zone_id)
        fc = current_forecast()
        if zone_id is not None:
            fc.zones = [z for z in fc.zones if z.zone_id == zone_id]
        return fc

    @app.get("/api/pilot/options", response_model=list[ZoneOptions])
    def pilot_options(zone_id: str | None = None):
        check_zone(zone_id)
        zones: list[ZoneForecast] = current_forecast().zones
        return [pilot.score_options(z) for z in zones if zone_id in (None, z.zone_id)]

    @app.get("/api/pilot/group", response_model=GroupResult)
    def pilot_group():
        return pilot.select_group()

    @app.get("/api/migrate/plan", response_model=MigratePlan)
    def migrate_plan():
        return migrate.plan(current_forecast())

    def default_tamper_index() -> int:
        """A fixed mid-chain reading in Z-NORTH-3, so the demo looks the same each time."""
        entries = led.all_entries()
        zes = [e for e in entries if e["reading"].get("zone_id") == "Z-NORTH-3"]
        return zes[len(zes) // 2]["index"]

    @app.post("/api/demo/tamper", response_model=TamperResult)
    def tamper(req: TamperRequest | None = None):
        require_demo()
        req = req or TamperRequest()
        idx = req.index if req.index is not None else default_tamper_index()
        # The tamper must keep the reading the right shape, so the UI can still show it.
        # (It only breaks the signature, which is the point.)
        if req.field not in Reading.model_fields:
            raise HTTPException(404, f"no field {req.field}")
        numeric = req.field in config.PRECISION or req.field in config.INT_FIELDS
        if numeric and (isinstance(req.value, bool) or not isinstance(req.value, (int, float))):
            raise HTTPException(422, f"{req.field} needs a number")
        if not numeric and not isinstance(req.value, str):
            raise HTTPException(422, f"{req.field} needs text")
        try:
            old, new = led.tamper(idx, req.field, req.value)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        return TamperResult(index=idx, field=req.field, old_value=old, new_value=new)

    @app.post("/api/demo/reset")
    def reset() -> dict[str, Any]:
        require_demo()
        led.clear()
        n = simulator.generate_ledger(led)
        return {"ok": True, "entries": n}

    return app


app = create_app()

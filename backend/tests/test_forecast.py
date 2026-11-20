import numpy as np

from app import config, forecast, simulator
from app.ledger import verify_chain


def test_fit_recovers_known_decay(clean_forecast):
    for z in clean_forecast.zones:
        _, pk, _, rk = config.ZONE_DECAY[z.zone_id]
        assert z.ok
        assert abs(z.pm25.fit["k"] - pk) / pk < 0.25
        assert abs(z.radiation.fit["k"] - rk) / rk < 0.25


def test_band_contains_mid(clean_forecast):
    for z in clean_forecast.zones:
        for p in z.pm25.projected:
            assert p.lo - 1e-6 <= p.mid <= p.hi + 1e-6


def test_safe_day_logic(clean_forecast):
    by = {z.zone_id: z for z in clean_forecast.zones}
    fastest = by["Z-NORTH-3"]
    assert fastest.safe_day is not None and 0 < fastest.safe_day <= config.FORECAST_HORIZON_DAYS
    assert fastest.safe_day == max(fastest.pm25.cross_day, fastest.radiation.cross_day)
    assert clean_forecast.first_safe_zone == "Z-NORTH-3"
    # Central's pm25 floor is right at the threshold: never safe within the horizon.
    assert by["Z-CENTRAL-1"].safe_day is None
    assert "Z-CENTRAL-1" not in clean_forecast.ranking


def test_interval_brackets_safe_day(clean_forecast):
    for z in clean_forecast.zones:
        if z.safe_day is not None and z.safe_day_lo is not None:
            assert z.safe_day_lo <= z.safe_day <= z.safe_day_hi


def test_reproducible(full_ledger, clean_forecast):
    entries = full_ledger.all_entries()
    _, st = verify_chain(entries, simulator.public_registry())
    again = forecast.forecast_all(entries, st)
    assert again.model_dump() == clean_forecast.model_dump()


def test_only_verified_data_used(full_ledger):
    entries = full_ledger.all_entries()
    _, st = verify_chain(entries, simulator.public_registry())
    st = {i: ("untrusted_after_break" if i >= 1440 else s) for i, s in st.items()}
    fc = forecast.forecast_all(entries, st)
    assert all(z.days_used == 30 for z in fc.zones)


def test_not_enough_data_is_visible():
    z = forecast.forecast_zone("Z-NORTH-3", {"pm25_ugm3": [(0, 50.0)], "radiation_usv_h": [(0, 1.0)]})
    assert not z.ok and "Not enough" in z.message


def test_decay_shape():
    t = np.array([0.0, 10.0])
    y = forecast.decay(t, 10.0, 0.1, 2.0)
    assert y[0] == 12.0 and y[1] < y[0]

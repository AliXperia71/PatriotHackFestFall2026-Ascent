import pytest

from app import simulator
from app.ledger import Ledger


@pytest.fixture()
def led(tmp_path):
    """A fresh ledger with a few readings (fast)."""
    ledger = Ledger(tmp_path / "t.db")
    from app import crypto
    import numpy as np

    rng = np.random.default_rng(1)
    for r in simulator.generate_readings(rng)[:60]:
        r = crypto.round_reading(r)
        ledger.append(r, crypto.sign(crypto.probe_private_key(r["probe_id"]), r))
    return ledger


@pytest.fixture()
def registry():
    return simulator.public_registry()


@pytest.fixture(scope="session")
def full_ledger(tmp_path_factory):
    """The full demo ledger (2880 entries), built once."""
    ledger = Ledger(tmp_path_factory.mktemp("full") / "full.db")
    simulator.generate_ledger(ledger)
    return ledger


@pytest.fixture(scope="session")
def clean_forecast(full_ledger):
    from app import forecast
    from app.ledger import verify_chain

    entries = full_ledger.all_entries()
    _, st = verify_chain(entries, simulator.public_registry())
    return forecast.forecast_all(entries, st)

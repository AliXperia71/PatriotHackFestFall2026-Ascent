from app import config, simulator


def test_probe_counts():
    ids = simulator.probe_ids()
    assert len(ids) == len(config.ZONES)
    assert sum(len(v) for v in ids.values()) == 12
    assert len(simulator.public_registry()) == 12


def test_generation_is_reproducible():
    import numpy as np

    a = simulator.generate_readings(np.random.default_rng(config.SEED))[:50]
    b = simulator.generate_readings(np.random.default_rng(config.SEED))[:50]
    assert a == b


def test_pm25_decays():
    import numpy as np

    rs = simulator.generate_readings(np.random.default_rng(config.SEED))
    z = [r["pm25_ugm3"] for r in rs if r["probe_id"] == "P-05"]
    assert z[-1] < z[0]

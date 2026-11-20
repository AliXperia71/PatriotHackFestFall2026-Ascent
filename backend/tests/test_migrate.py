from collections import defaultdict

from app import config, migrate


def test_caps_respected(clean_forecast):
    p = migrate.plan(clean_forecast)
    per_wave = defaultdict(int)
    per_zone_wave = defaultdict(int)
    per_zone = defaultdict(int)
    for r in p.rows:
        per_wave[r.wave] += r.population
        per_zone_wave[(r.destination, r.wave)] += r.population
        per_zone[r.destination] += r.population
    assert all(v <= config.SUPPLY_PER_WAVE for v in per_wave.values())
    assert all(v <= config.ZONE_INTAKE_PER_WAVE for v in per_zone_wave.values())
    assert all(v <= config.ZONE_CAPACITY for v in per_zone.values())


def test_everyone_accounted_for(clean_forecast):
    p = migrate.plan(clean_forecast)
    assert p.placed + sum(p.unplaced.values()) == p.total_population


def test_deep_levels_go_first(clean_forecast):
    p = migrate.plan(clean_forecast)
    first = {}
    for r in p.rows:
        first.setdefault(r.level, r.wave)
    levels = sorted(first)
    # a deeper level never starts later than a shallower one
    assert all(first[a] >= first[b] for a, b in zip(levels, levels[1:]))
    assert p.rows[0].level == config.HOLLOW_LEVELS


def test_zone_only_used_after_it_opens(clean_forecast):
    p = migrate.plan(clean_forecast)
    for r in p.rows:
        ow = p.zone_open_wave[r.destination]
        assert ow is not None and r.wave >= ow
    assert p.zone_open_wave["Z-CENTRAL-1"] is None


def test_open_wave():
    assert migrate.open_wave(None, 60) is None
    assert migrate.open_wave(10, 60) == 1
    assert migrate.open_wave(91, 60) == 3

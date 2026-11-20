from app import config, pilot


def test_weights_sum_to_one():
    assert abs(sum(config.OPTION_WEIGHTS.values()) - 1) < 1e-9
    assert abs(sum(config.GROUP_WEIGHTS.values()) - 1) < 1e-9


def test_option_contributions_add_up(clean_forecast):
    for z in clean_forecast.zones:
        res = pilot.score_options(z)
        assert len(res.options) == 3
        for o in res.options:
            assert abs(sum(o.contributions.values()) - o.total) < 1e-3
            assert all(0 <= v <= 1 for v in o.normalized.values())
        viable = [o for o in res.options if o.viable]
        if viable:
            assert res.recommended == max(viable, key=lambda o: o.total).option


def test_dirtier_zone_needs_more_protection(clean_forecast):
    by = {z.zone_id: pilot.score_options(z) for z in clean_forecast.zones}
    assert by["Z-NORTH-3"].recommended == "suit"
    assert by["Z-CENTRAL-1"].recommended == "outpost"


def test_no_forecast_no_options():
    from app.models import ZoneForecast

    zf = ZoneForecast(zone_id="Z-NORTH-3", name="x", ok=False, message="no data", days_used=0, last_day=0)
    res = pilot.score_options(zf)
    assert res.recommended is None and res.options == [] and "no data" in res.note


def test_group_only_eligible_and_explained():
    g = pilot.select_group()
    assert len(g.selected) == config.GROUP_SIZE
    assert g.eligible + sum(g.excluded.values()) == g.pool_size
    for c in g.selected:
        assert pilot.exclusion_reason(c.person) is None
        assert abs(sum(c.contributions.values()) - c.score) < 1e-3
        assert c.score >= g.band_cutoff


def test_group_reproducible_and_seed_changes_it():
    a = [c.person.person_id for c in pilot.select_group().selected]
    assert a == [c.person.person_id for c in pilot.select_group().selected]
    assert a != [c.person.person_id for c in pilot.select_group(seed=1).selected]

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db = tmp_path_factory.mktemp("api") / "api.db"
    with TestClient(create_app(db_path=db, demo_mode=True)) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset(client):
    client.post("/api/demo/reset")


def test_health(client):
    j = client.get("/api/health").json()
    assert j["ok"] and j["entries"] == 2880


def test_zones_and_readings(client):
    zones = client.get("/api/zones").json()
    assert len(zones) == 6 and all(z["status"] == "verified" for z in zones)
    rs = client.get("/api/readings", params={"zone_id": "Z-NORTH-3", "limit": 5}).json()
    assert len(rs) == 5
    assert all(r["reading"]["zone_id"] == "Z-NORTH-3" and r["status"] == "verified" for r in rs)
    assert rs[0]["index"] > rs[-1]["index"]  # newest first


def test_unknown_zone_404(client):
    assert client.get("/api/readings", params={"zone_id": "nope"}).status_code == 404


def test_verify_clean(client):
    j = client.get("/api/verify").json()
    assert j["ok"] and j["first_bad_index"] is None


def test_tamper_flags_right_entry(client):
    t = client.post("/api/demo/tamper").json()
    v = client.get("/api/verify").json()
    assert not v["ok"]
    assert v["first_bad_index"] == t["index"]
    assert v["reason"] == "bad_signature"
    one = client.get(f"/api/verify/{t['index']}").json()
    assert one["status"] == "tampered" and not one["signature_valid"]
    after = client.get(f"/api/verify/{t['index'] + 1}").json()
    assert after["status"] == "untrusted_after_break"
    before = client.get(f"/api/verify/{t['index'] - 1}").json()
    assert before["status"] == "verified" and before["signature_valid"]
    zones = {z["zone_id"]: z["status"] for z in client.get("/api/zones").json()}
    assert zones["Z-NORTH-3"] == "tampered"


def test_tamper_is_repeatable(client):
    a = client.post("/api/demo/tamper").json()["index"]
    client.post("/api/demo/reset")
    b = client.post("/api/demo/tamper").json()["index"]
    assert a == b


def test_reset_restores(client):
    client.post("/api/demo/tamper")
    client.post("/api/demo/reset")
    assert client.get("/api/verify").json()["ok"]


def test_demo_endpoints_blocked_without_demo_mode(tmp_path):
    with TestClient(create_app(db_path=tmp_path / "x.db", demo_mode=False)) as c:
        assert c.post("/api/demo/tamper").status_code == 403
        assert c.post("/api/demo/reset").status_code == 403
        assert c.get("/api/verify").json()["ok"]


def test_tamper_bad_field_404(client):
    r = client.post("/api/demo/tamper", json={"index": 3, "field": "nope", "value": 1})
    assert r.status_code == 404


def test_forecast_endpoint(client):
    j = client.get("/api/forecast").json()
    assert j["first_safe_zone"] == "Z-NORTH-3" and len(j["zones"]) == 6
    one = client.get("/api/forecast", params={"zone_id": "Z-EAST-2"}).json()
    assert [z["zone_id"] for z in one["zones"]] == ["Z-EAST-2"]
    assert client.get("/api/forecast", params={"zone_id": "nope"}).status_code == 404


def test_forecast_shrinks_after_tamper(client):
    client.post("/api/demo/tamper")
    j = client.get("/api/forecast").json()
    assert all(z["days_used"] < 60 for z in j["zones"])


def test_pilot_endpoints(client):
    opts = client.get("/api/pilot/options", params={"zone_id": "Z-CENTRAL-1"}).json()
    assert len(opts) == 1 and opts[0]["recommended"] == "outpost"
    g = client.get("/api/pilot/group").json()
    assert len(g["selected"]) == 20


def test_migrate_endpoint(client):
    p = client.get("/api/migrate/plan").json()
    assert p["placed"] + sum(p["unplaced"].values()) == p["total_population"]
    assert p["rows"][0]["level"] == 8


def test_tamper_rejects_wrong_type(client):
    r = client.post("/api/demo/tamper", json={"index": 5, "field": "pm25_ugm3", "value": "abc"})
    assert r.status_code == 422
    r = client.post("/api/demo/tamper", json={"index": 5, "field": "probe_id", "value": 3})
    assert r.status_code == 422
    assert client.get("/api/verify").json()["ok"]


def test_tamper_probe_id_swap_is_caught(client):
    client.post("/api/demo/tamper", json={"index": 5, "field": "probe_id", "value": "P-12"})
    v = client.get("/api/verify").json()
    assert v["first_bad_index"] == 5 and v["reason"] == "bad_signature"
    assert client.get("/api/readings", params={"limit": 500}).status_code == 200

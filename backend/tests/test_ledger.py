import sqlite3

from app import crypto, ledger as L


def verify(led, registry):
    return L.verify_chain(led.all_entries(), registry)


def test_clean_chain_passes(led, registry):
    res, st = verify(led, registry)
    assert res.ok and res.first_bad_index is None and res.total == 60
    assert set(st.values()) == {"verified"}


def test_genesis_prev_is_zeros(led):
    assert led.get(0)["prev_hash"] == "0" * 64


def test_edit_reading_flags_exact_entry_and_rest(led, registry):
    led.tamper(20, "pm25_ugm3", 1.0)
    res, st = verify(led, registry)
    assert not res.ok
    assert res.first_bad_index == 20
    assert res.reason == "bad_signature"
    assert st[19] == "verified"
    assert st[20] == "tampered"
    assert all(st[i] == "untrusted_after_break" for i in range(21, 60))
    assert res.untrusted_count == 39


def test_edit_first_entry(led, registry):
    led.tamper(0, "co_ppm", 99.0)
    res, _ = verify(led, registry)
    assert res.first_bad_index == 0


def test_deleted_entry_breaks_link(led, registry):
    led.delete_entry(10)
    res, _ = verify(led, registry)
    assert res.first_bad_index == 11
    assert res.reason == "prev_hash_mismatch"


def test_edited_entry_hash_is_caught(led, registry):
    with sqlite3.connect(led.db_path) as c:
        c.execute("UPDATE entries SET entry_hash = ? WHERE idx = 5", ("ab" * 32,))
    res, _ = verify(led, registry)
    assert res.first_bad_index == 5
    assert res.reason == "entry_hash_mismatch"


def test_resigned_with_wrong_key_is_caught(led, registry):
    e = led.get(7)
    forged = crypto.sign(crypto.probe_private_key("P-12"), e["reading"])
    with sqlite3.connect(led.db_path) as c:
        c.execute("UPDATE entries SET signature = ? WHERE idx = 7", (forged,))
    res, _ = verify(led, registry)
    assert res.first_bad_index == 7 and res.reason == "bad_signature"


def test_unknown_probe(led, registry):
    reg = {k: v for k, v in registry.items() if k != led.get(3)["reading"]["probe_id"]}
    res, _ = L.verify_chain(led.all_entries(), reg)
    assert res.first_bad_index == 3 and res.reason == "unknown_probe"


def test_malformed_signature_does_not_crash(led, registry):
    with sqlite3.connect(led.db_path) as c:
        c.execute("UPDATE entries SET signature = 'not-hex' WHERE idx = 2")
    res, _ = verify(led, registry)
    assert res.first_bad_index == 2

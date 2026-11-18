from app import crypto

R = {
    "probe_id": "P-01", "zone_id": "Z-NORTH-3", "ts": "2087-03-14T06:00:00Z",
    "pm25_ugm3": 12.4, "o2_pct": 20.7, "co_ppm": 0.8,
    "radiation_usv_h": 0.21, "temp_c": 14.2, "machine_contacts": 0,
}


def test_canonical_ignores_key_order():
    shuffled = dict(reversed(list(R.items())))
    assert crypto.canonicalize(R) == crypto.canonicalize(shuffled)


def test_float_rounding_is_stable():
    noisy = {**R, "pm25_ugm3": 12.400000001, "temp_c": 14.199999999}
    assert crypto.canonicalize(noisy) == crypto.canonicalize(R)


def test_sign_verify_round_trip():
    priv = crypto.probe_private_key("P-01")
    sig = crypto.sign(priv, R)
    assert crypto.verify_sig(crypto.public_key_hex(priv), R, sig)


def test_tampered_reading_fails():
    priv = crypto.probe_private_key("P-01")
    sig = crypto.sign(priv, R)
    assert not crypto.verify_sig(crypto.public_key_hex(priv), {**R, "pm25_ugm3": 1.0}, sig)


def test_wrong_key_fails():
    sig = crypto.sign(crypto.probe_private_key("P-01"), R)
    other = crypto.public_key_hex(crypto.probe_private_key("P-02"))
    assert not crypto.verify_sig(other, R, sig)


def test_garbage_signature_does_not_crash():
    pub = crypto.public_key_hex(crypto.probe_private_key("P-01"))
    assert not crypto.verify_sig(pub, R, "zz")


def test_keys_are_deterministic():
    a = crypto.public_key_hex(crypto.probe_private_key("P-01"))
    assert a == crypto.public_key_hex(crypto.probe_private_key("P-01"))
    assert a != crypto.public_key_hex(crypto.probe_private_key("P-02"))

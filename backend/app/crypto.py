"""Keys, canonical bytes, signing and hashing.

`canonicalize()` is the ONLY place that makes bytes to sign or hash.
The signer and the verifier both call it.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from . import config

GENESIS_PREV: str = "0" * 64


def round_reading(reading: dict[str, Any]) -> dict[str, Any]:
    """Round numeric fields to fixed precision so float noise never changes the bytes."""
    out: dict[str, Any] = dict(reading)
    for name, places in config.PRECISION.items():
        if name in out:
            out[name] = round(float(out[name]), places) + 0.0  # +0.0 turns -0.0 into 0.0
    for name in config.INT_FIELDS:
        if name in out:
            out[name] = int(out[name])
    return out


def canonicalize(reading: dict[str, Any]) -> bytes:
    rounded = round_reading(reading)
    return json.dumps(rounded, sort_keys=True, separators=(",", ":")).encode("utf-8")


def probe_private_key(probe_id: str) -> Ed25519PrivateKey:
    """Deterministic DEMO key per probe. Synthetic, never a real secret."""
    seed = hashlib.sha256(f"ascent-demo:{config.SEED}:{probe_id}".encode()).digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def public_key_hex(priv: Ed25519PrivateKey) -> str:
    raw = priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return raw.hex()


def sign(priv: Ed25519PrivateKey, reading: dict[str, Any]) -> str:
    return priv.sign(canonicalize(reading)).hex()


def verify_sig(pub_hex: str, reading: dict[str, Any], sig_hex: str) -> bool:
    try:
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex))
        pub.verify(bytes.fromhex(sig_hex), canonicalize(reading))
        return True
    except (InvalidSignature, ValueError, KeyError, TypeError):
        return False


def compute_entry_hash(prev_hash: str, reading: dict[str, Any], sig_hex: str) -> str:
    """sha256(prev_hash || canonical_reading || signature), all as raw bytes."""
    h = hashlib.sha256()
    h.update(bytes.fromhex(prev_hash))
    h.update(canonicalize(reading))
    h.update(bytes.fromhex(sig_hex))
    return h.hexdigest()

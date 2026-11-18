# Ascent

**Trust math, not the Directorate.**

It is the year 2087. Two billion people live in the Hollow, deep underground. The Directorate says the surface will kill you in minutes. Many people think it has healed. Who is right?

Ascent has three steps:

1. **Prove** - Is the surface safe? Probes on the surface send readings. Each reading is signed. Anyone can check the signs.
2. **Pilot** - Which way of living up top works best, and who goes first? *(coming Wed)*
3. **Migrate** - Plan the move up, in waves. *(coming Wed)*

Built for the Virtual GMU "Life Underground" track.

> Status: **Prove works end to end.** Pilot and Migrate are not built yet.

---

## Run the demo (3 commands)

You need Python 3.11 or newer, and Node 20 or newer.

**1. Set up the backend (once)**

```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

**2. Start the backend** (same terminal)

```bash
DEMO_MODE=1 uvicorn app.main:app --reload
```

**3. Start the frontend** (new terminal, from the project folder)

```bash
cd frontend && npm install && npm run dev
```

Then open http://localhost:5173

The first run makes the data by itself (about 1 second).

### Try the tamper demo

1. Open the page. The top bar is green: "All 2880 readings verified."
2. Click a zone on the map. See its latest readings with green badges.
3. Click **Verify** on one row. You see: signature OK, link OK, hash OK.
4. Click **Tamper**. The demo changes one stored reading in secret.
5. The top bar turns red. It names the exact bad entry. Every entry after it turns gray ("untrusted").
6. Click **Reset** to go back to a clean log.

The Tamper and Reset buttons only work when you start the backend with `DEMO_MODE=1`.

---

## How Prove works (in plain words)

1. **Each probe has a key pair.** The private key stays with the probe. The public key is open to everyone.
2. **A probe signs each reading.** The signature is a stamp that only that probe can make. If someone changes even one number, the stamp no longer fits.
3. **Readings go into a chain.** Each log entry holds a "hash" of the entry before it. A hash is a short fingerprint. If you change an old entry, its fingerprint changes, and the chain breaks.
4. **Anyone can verify.** The checker looks at every entry, in order. It checks three things:
   - the signature fits the reading,
   - the entry points to the right earlier entry,
   - the fingerprint is correct.
5. **It reports the first bad entry.** After a break, we cannot trust the entries after it. We mark them "untrusted."

The fingerprint of an entry is: `sha256(previous_hash + reading + signature)`.

Before signing, every reading is put in one fixed form (sorted keys, rounded numbers). The signer and the checker use the same code for this: `canonicalize()` in `backend/app/crypto.py`.

> The keys here are fake keys for the demo. They are made from a fixed seed so the demo repeats. They are not real secrets.

---

## Project map

```
backend/app/
  config.py      settings, thresholds, zone list
  models.py      data shapes (Pydantic)
  crypto.py      keys, sign, verify, canonicalize
  ledger.py      the hash chain (SQLite) + verify_chain()
  simulator.py   fake probes and fake surface data
  main.py        the web API
backend/tests/   pytest tests
frontend/src/    React + Leaflet map
data/            the SQLite file (made at first run, not in git)
```

Fake data: 6 zones, 12 probes, 60 days, 4 readings a day = 2880 readings.

---

## API (for the frontend)

| Call | What it does |
|------|--------------|
| `GET /api/health` | Is the server up? Is demo mode on? |
| `GET /api/zones` | Each zone, its map spot, its latest reading, its status |
| `GET /api/readings?zone_id=Z-NORTH-3&limit=20` | Readings (newest first) with a status |
| `GET /api/verify` | Check the whole chain. Gives the first bad index and why |
| `GET /api/verify/{index}` | Check one entry (the "Verify" button) |
| `GET /api/probes` | The public keys |
| `POST /api/demo/tamper` | Edit one stored reading (demo mode only) |
| `POST /api/demo/reset` | Make a clean log again (demo mode only) |

Status values: `verified`, `tampered`, `untrusted_after_break`.

Example from `/api/verify` after a tamper:

```json
{
  "ok": false,
  "total": 2880,
  "checked": 1441,
  "first_bad_index": 1440,
  "reason": "bad_signature",
  "untrusted_count": 1439
}
```

Reasons: `unknown_probe`, `malformed_reading`, `bad_signature`, `prev_hash_mismatch`, `entry_hash_mismatch`.

The frontend dev server forwards `/api/...` to the backend on port 8000, so the frontend code just calls `/api/...`. The types are in `frontend/src/api.ts` and match `backend/app/models.py`.

---

## Run the tests

```bash
cd backend && source .venv/bin/activate && pytest -q
```

They cover signing, the chain, the tamper case, and the API.

---

## Important notes

- **Safety thresholds are illustrative.** They are not medical advice.
- **All data is synthetic.** No real people, places, or readings.
- Everything is seeded (`SEED = 2087` in `config.py`), so every demo run looks the same.

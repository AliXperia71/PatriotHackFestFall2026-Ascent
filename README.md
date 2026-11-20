# Ascent

**Trust math, not the Directorate.**

It is the year 2087. Two billion people live in the Hollow, deep underground. The Directorate says the surface will kill you in minutes. Many people think it has healed. Who is right?

Ascent has three steps:

1. **Prove** - Is the surface safe? Probes on the surface send readings. Each reading is signed. Anyone can check the signs. A forecast then says when each zone should be safe.
2. **Pilot** - Which way of living up top works best (suit, dome or sealed outpost)? Who goes first? Every score shows its parts, so there is no black box.
3. **Migrate** - Plan the move up, in waves. The deepest levels go first.

Built for the Virtual GMU "Life Underground" track.

> Status: **All parts work end to end.** Prove, Forecast, Pilot and Migrate. 53 tests pass.

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

### The demo script (about 3 minutes)

The page has 4 tabs at the top. Go left to right.

**Tab 1 - Prove**
1. The top bar is green: "All 2880 readings verified."
2. Click a zone on the map. You see its latest readings, each with a green badge.
3. Click **Verify** on one row. You see: signature OK, link OK, hash OK.

**Tab 2 - Forecast**
4. The map shows each zone's projected safe date. The panel says which zone is safe first (North Ridge, Z-NORTH-3).
5. Click a zone to see its curves. Dots are real readings. The line is the fit. The blue band is the range of likely outcomes. The green dashed line is the safe level.
6. Point out Central Plain: it is **not** projected safe within a year. The math does not just say "yes" to everything.

**Tab 3 - Pilot**
7. Click a zone. See suit vs dome vs outpost. Each bar is split into colored parts: safety, cost, capacity, time. Clean zones get suits. Dirty zones need outposts.
8. Scroll down to "Who goes first?": 300 people, then only eligible people, then the top 40, then a fair lottery picks 20. Each person's bar shows why.

**Tab 4 - Migrate**
9. The map shows which wave each zone opens in. The panel shows people moved per wave, never over the limit. Level 8 (the deepest) goes first.

**Back to Tab 1 - the tamper moment (save it for last)**
10. Click **Tamper**. The demo changes one stored reading in secret.
11. The top bar turns red. It names the exact bad entry (#1440). Every entry after it turns gray ("untrusted").
12. Bonus: open Forecast again. It now uses only the trusted readings (30 days, not 60). Bad data cannot sneak into the plan.
13. Click **Reset** to go back to a clean log.

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
  forecast.py    recovery forecast (curve fit + uncertainty band)
  pilot.py       option scores + fair group pick
  migrate.py     wave planner
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
| `GET /api/forecast?zone_id=` | Safe date, curve and band per zone, plus the first zone to be safe |
| `GET /api/pilot/options?zone_id=` | Suit / dome / outpost scores, with each criterion's part |
| `GET /api/pilot/group` | The first group of 20, and why each person was picked |
| `GET /api/migrate/plan` | Wave schedule: from level, to zone, how many people, which wave |
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

## How Forecast, Pilot and Migrate work (in plain words)

**Forecast** (`forecast.py`)
- It only uses **verified** readings. If the chain breaks, the forecast drops everything after the break.
- For each zone, it takes the daily average of PM2.5 (dust) and radiation.
- It fits a curve that drops fast and then levels off: `level = floor + a * e^(-k * day)`.
- It tries 400 slightly different curves (based on how sure the fit is). That gives the blue band and the date range.
- A zone is "safe" on the first day both PM2.5 and radiation are under their limits.

**Pilot: which option?** (`pilot.py`)
- Each option gets 4 scores from 0 to 1: **safety** (how far under the limit people stay, after the option's protection), **cost**, **capacity** and **time to set up**.
- Each score is multiplied by its weight (safety 0.45, cost 0.20, capacity 0.20, time 0.15). The parts add up to the total.
- An option with a safety score under 0.20 is marked "not safe" and cannot be picked.

**Pilot: who goes first?** (`pilot.py`)
1. **Filter:** only volunteers, ages 18-60, with good health.
2. **Score:** health, a needed skill (engineer, medic, builder), how deep they live, and years underground. Deep levels count more because they suffer most.
3. **Lottery:** a seeded lottery picks 20 from the top 40. Close scores should not decide everything. The seed makes it repeatable and checkable.

**Migrate** (`migrate.py`)
- A zone opens in the first wave after the **late end** of its safe-date range. We play it safe.
- One wave every 30 days. Limits: 12,000 people per wave in total, 5,000 per zone per wave, 25,000 per zone overall.
- It fills each wave starting with the deepest level. It reports anyone it could not place.
- This is a simple "greedy" planner on purpose. It is easy to explain and easy to check.

All the numbers above live in `backend/app/config.py`. Change them there.

---

## Run the tests

```bash
cd backend && source .venv/bin/activate && pytest -q
```

They cover signing, the chain, the tamper case, the forecast, Pilot, Migrate and the API.

---

## Important notes

- **Safety thresholds are illustrative.** They are not medical advice.
- **All data is synthetic.** No real people, places, or readings.
- **Known limits:** the data is made up and follows the same curve shape we fit, so the fit looks better than it would on real data. Migrate is greedy, not a perfect optimizer. The probe keys are made from a seed, which is fine for a demo but never for real use.
- Everything is seeded (`SEED = 2087` in `config.py`), so every demo run looks the same.
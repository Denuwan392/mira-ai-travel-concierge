# Cultural Triangle Quote, Enquiry Identity, and A2UI Context Repair Report

**Date:** 2026-11-25  
**Scope:** Issues 1–8 (Cultural Triangle `T09` pricing, chat vs tour-detail parity, active-tour A2UI preservation, `4fa58796-73e7-40c0-a547-46d75755f3a0` forensic investigation, enquiry reference alignment, live backend revision check, and regression verification).

---

## 1. Exact Pricing Decision for Cultural Triangle (`2027-01-10`, 4 Adults, 3 Children `[7, 7, 7]`)

- **Tour ID / Title:** `T09` — *Cultural Triangle Sri Lanka Package* (7 days / 6 nights; hotel schedule: `H12, H12, H02, H02, H03, H03`)
- **Outcome:** **`PRICE_UNAVAILABLE`** (`Unavailable("hotel_rate_missing_or_ambiguous")`) — **legitimate fail-closed specialist handoff**.
- **Workbook Evidence (`rate_sheet_2026-27.xlsx`):**
  - Nights 1–2 (`2027-01-10`, `2027-01-11`, `H12` *Anuradhapura Heritage Lodge*): 1 matching row (Row 49, Peak).
  - Nights 3–4 (`2027-01-12`, `2027-01-13`, `H02` *Sigiriya Village*): 1 matching row (Row 9, Peak).
  - Nights 5–6 (`2027-01-14`, `2027-01-15`, `H03` *Hotel Suisse*): **2 overlapping Peak-season rows**:
    - **Row 13:** `2026-12-15` to `2027-03-31` (`30,000 / 24,000 / 6,500`, note: `None`)
    - **Row 56:** `2027-01-01` to `2027-03-31` (`34,000 / 27,000 / 7,000`, note: `'Revised per supplier email?'`)
  - Because `mira.data.one(...)` requires exactly one unambiguous contract row per night, `T09` on `2027-01-10` fails closed for all party sizes (`2+0`, `2+2`, `4+0`, `4+3`).
- **Contrast on Valid Date (`2027-04-12`):** `data.price("T09", date(2027, 4, 12), 4, [7, 7, 7], date(2026, 11, 19))` resolves deterministically to **USD 4,530** (deposit **USD 1,133**).

---

## 2. Chat vs Tour-Detail Parity & Root Causes

| Aspect | Before Repair (Observed in Trace `9683bd38...`) | After Repair |
|---|---|---|
| **Intent & Routing** | `notebook_intent` returned `operation="plan"`; `agent.py:439-455` popped `ctx["tour"]` and forced `action="custom"` | Active-tour quote turns (`ctx["tour"] in tours`) guard against `notebook_intent` hijack and never fall back to `action="custom"` |
| **TourCards Rendered** | `T03` (Colombo City Tour), `T09` (Cultural Triangle), `T16` (Galle Fort) | Only `T09` (active selected tour preserved in both chat and `Workspace.jsx`) |
| **Customer Explanation** | Generic `"We can't verify an automated price..."` | Explicit rate-sheet reason (`hotel_rate_missing_or_ambiguous` → unconfirmed/overlapping hotel rates) |
| **Chat vs Tour-Detail Outcome** | Chat went to `custom` (`T03/T09/T16`); Tour-Detail hit `REQUEST_QUOTE` | Both hit `quote_node` -> `data.price()`, returning identical `PRICE_UNAVAILABLE` (`T09`, `hotel_rate_missing_or_ambiguous`) on `2027-01-10` and `USD 4,530` on `2027-04-12` |

---

## 3. Forensic Investigation of `4fa58796-73e7-40c0-a547-46d75755f3a0`

- **Database Row Found:** `enquiries.id = "4fa58796-73e7-40c0-a547-46d75755f3a0"`
  - `enquiries.trace = "9683bd38-3dc5-4c29-84f8-ddeb34840700"`
  - `enquiries.quote = null`, `enquiries.trip = "{}"`, `enquiries.reason = "custom_or_unsupported"`, `enquiries.status = "new"`
  - `enquiries.created = "2026-11-24 19:46:37"`, `enquiries.reference = null`, `enquiries.updated_at = null`
- **Identity Relationship Diagram:**
  ```text
  visitors.id (b0RNGU2U...)
    └─▶ traces.id (9683bd38-3dc5-4c29-84f8-ddeb34840700)
          └─▶ enquiries.id (4fa58796-73e7-40c0-a547-46d75755f3a0)
                ├─ reference: NULL (created by stale PID 18762 before 0006/persist update)
                └─ Notice.reference emitted UUID; Staff UI displayed 4fa58796... (id[:8])
  ```
- **Root Causes:**
  1. **Stale Live Backend (`PID 18762` on port `8000`):** Started before our `agent.py` `INSERT INTO enquiries(id, reference, ...)` update, so it inserted `reference=NULL`.
  2. **Notice UUID vs Public `ENQ-...` Reference:** `Notice.reference` was the raw `enquiries.id` UUID, while `StaffConsole` displayed `enquiries.reference` (`ENQ-2026-...` or `id[:8]` fallback `4fa58796...`).
  3. **Staff Endpoint UUID-Only Validation:** `GET /api/staff/enquiries/{key}` and `PATCH /api/staff/enquiries/{key}` typed `key: UUID`, rejecting `ENQ-2026-...` public references.
- **Repairs Implemented:**
  - Added `public_reference` (`ENQ-YYYY-XXXXXXXX`), `outcome`, `reason_code`, and `tour_id` to `Notice` in `apps/api/mira/catalog.py` and populated them in `apps/api/mira/agent.py`.
  - Updated `GET/PATCH /api/staff/enquiries/{key}` in `apps/api/mira/main.py` to resolve `WHERE id=? OR reference=?` and updated `Workspace.jsx` (`TourDetailPage`, `MiraWorkspace`, `UIComponentRenderer`) to display and navigate with `public_reference || reference`.

---

## 4. Live Backend & Stale Process Verification (Issue 7)

- Observed pre-existing processes listening via `lsof`: `Python` PID `18762` (`127.0.0.1:8000`), `node` PID `18764` (`127.0.0.1:5175`), `node` PID `18765` (`127.0.0.1:3000`).
- Added `"revision": "rc-2026-11-25"` (via `MIRA_BUILD_REV`, no internal filesystem paths or secrets) to `GET /api/health` in `apps/api/mira/main.py` so any caller or browser test can verify whether the running backend matches the current build.
- **Important Operational Note:** Before using the interactive browser on ports `8000` / `5175` / `3000`, restart `make dev` so PIDs `18762`, `18764`, and `18765` are replaced by the newly built backend and workspace bundle.

---

## 5. Modified Files

- `apps/api/mira/catalog.py` — Extended `Notice` with `public_reference`, `outcome`, `reason_code`, `tour_id`.
- `apps/ceylon-compass/src/lib/live/catalog.ts` & `apps/web/lib/catalog.ts` — Updated strict Zod `EnquiryNotice` schema to accept `public_reference`, `outcome`, `reason_code`, `tour_id`.
- `apps/api/mira/agent.py` — Guarded active-tour quote turns against `action="custom"` / `notebook_intent` hijack (`not active_tour_quote_turn`); added truthful `hotel_rate_missing_or_ambiguous` / `tour` explanations and `Notice` metadata.
- `apps/api/mira/main.py` — Updated `GET/PATCH /api/staff/enquiries/{key}` to accept `ENQ-...` or UUID; added safe `revision` to `GET /api/health`.
- `apps/ceylon-compass/workspace/Workspace.jsx` — Preserved `activeTour` against unrelated `TourCard` replacement during active quote/handoff turns; preferred `public_reference` for customer display and `/enquiry/{ref}` links.
- `apps/api/tests/test_cultural_triangle_identity_regression.py` — Added 4 regression tests covering Issues 1–8.

---

## 6. Verification Results (Post-Final-Edit)

- **Lint & Typecheck (`make lint`):** Passed (`compileall`, `apps/web` `tsc --noEmit`, `apps/ceylon-compass` `tsc --noEmit`).
- **Backend Tests (`make test` → `pytest`):** **210 passed, 0 failed** (including 4/4 in `test_cultural_triangle_identity_regression.py`).
- **Frontend Tests (`make test` → `vitest run --pool=threads`):** **61 passed across 8 files, 0 failed**.
- **Real Browser E2E (`make workspace-browser`):** **8/8 Playwright Chromium tests passed in 15.1s** against freshly launched Nitro (`15175`) + FastAPI (`18008`) servers.
- **Evaluation Suite (`evals/runner.py`):** **53/54 passed (98.1%)**, **63/63 validated turns** (sole failure: documented `P03` / `Q-1043`).
- **Dataset Integrity (`shasum -a 256 -c docs/source-sha256.txt`):** **39/39 OK**.
- **Remaining Limitations:** Pre-existing `make dev` processes (PIDs `18762`, `18764`, `18765`) on ports `8000`/`5175`/`3000` must be restarted with `make dev` to serve the updated code on default dev ports; automated screenshot capture (`MIRA_SCREENSHOTS=1`) was not re-run in this pass.

# Live pricing blockage repair

## Confirmed root cause

The local traveller workspace was proxying to a Python process started on November 24 at 03:11:17. Its health response omitted the revision field present in the current checkout. The saved traces for all three incident requests show the structured `REQUEST_QUOTE` message entering Gemini intent and suggestions, retrieval, UI validation and persistence. They contain no pricing stage. The response sent a generic specialist notice with recommendations unrelated to the selected configuration. Current workbook calculations verify all three configurations.

The old backend emitted `4fa58796…` in the saved responses for both T01 and T03 and for other requests on the same trip. On the forensic database copy, that UUID exists in `enquiries.id`, has reason `custom_or_unsupported`, has an empty trip configuration and no quote or stored public reference, and joins to a trace on the affected trip. The most recent association was the failing T01 turn. The browser's old renderer displayed the first eight characters of the UUID returned in the turn. The repeated reference had a database and response origin. The old component could also retain a notice across a party edit and only guarded against another button submit, which allowed an in-flight response to land after a configuration change.

## Runtime configuration

| Item | Before | Acceptance |
| --- | --- | --- |
| API, 127.0.0.1:8000 | PID 18762, Python `-u -m mira.serve`, working directory at checkout root | `make dev`, same module, revision `live-pricing-repair-r4` |
| Traveller frontend, 127.0.0.1:5175 | PID 18764, Vite dev with strict port | Vite dev under the restarted supervisor |
| Secondary frontend, 127.0.0.1:3000 | PID 18765, Next.js 16.4.6 dev | Next.js under the same supervisor |
| Traveller route | `/workspace/index.html#/tours/<slug>` | Same workspace route |
| API proxy | Vite `/api` to `http://127.0.0.1:8000` | Health verified through the Vite proxy |
| SQLite | Default `.mira/mira.sqlite3`, no `MIRA_DB` override in the development environment file. Incident records verified in a copy. | `MIRA_DB=/tmp/mira-pricing-acceptance.sqlite3` |
| Workspace bundle | `index-BHPNlY0J.js` | `index-C2qssms-.js`, rebuilt by `make dev` |
| Health | HTTP 200, rates loaded, 41 published records, revision absent | HTTP 200, rates loaded, 30 published records, 17 seed records, no missing inputs, local tracing |
| Pricing date | `AS_OF_DATE=2026-11-19` | `AS_OF_DATE=2026-11-19` |

The clean acceptance database starts from the supplied dataset, so the published-record count differs from the historical instance. The supplied workbook and original incident database were preserved. During an intermediate restart, the development environment file selected the separate `.mira/demo.sqlite3` instead of the requested temporary database. The delayed-response browser test wrote synthetic quotes there before the mismatch was identified. Those records were retained. The final run confirmed the temporary database through both direct and proxied health responses. A fresh Chrome context on the original workspace had empty local and session storage. The application uses session storage for the active trip ID and server-backed, ownership-filtered quote history. The original traveller's browser profile and cache were unavailable for direct inspection.

## Pricing comparison

All cases used January 10, 2027 and zero infants. Staff preview used a test staff account authenticated through the normal login endpoint. The browser verified that the persisted traveller pricing event and the staff preview both used digest `a16dd63ffb7ed2324e9d709f4b35e1bb3f0d5c2123b765903bce039f5fefdfe2`, which also matched the direct workbook load. The pricing function is an in-process call.

| Case | Resolved published tour | Adults | Child ages | Direct total / deposit | Staff preview HTTP 200 | Traveller HTTP 200 |
| --- | --- | ---: | --- | --- | --- | --- |
| A | T01, Sigiriya and Minneriya Day Tour from Kandy | 2 | [] | USD 315 / 315 | Verified, USD 315 / 315 | Verified, USD 315 / 315 |
| B | T01, Sigiriya and Minneriya Day Tour from Kandy | 4 | [] | USD 540 / 540 | Verified, USD 540 / 540 | Verified, USD 540 / 540 |
| C | T03, Colombo City Tour | 2 | [7, 7, 7, 7, 7, 7] | USD 265 / 265 | Verified, USD 265 / 265 | Verified, USD 265 / 265 |

Redacted browser evidence records the normalized request and response for [Case A](live-pricing/sigiriya-two.redacted.json), [Case B](live-pricing/sigiriya-four.redacted.json) and [Case C](live-pricing/colombo-six-children.redacted.json).

The verified cases have zero balance and no unavailable reason. The browser also received and displayed `date_or_fx_expired` for Colombo on January 10, 2029 and `tour_rate` for InstaFamous Sri Lanka (T10) on January 10, 2027. The latter has no automated workbook rate row. An injected HTTP 503 produced a retryable error without a quote or a saved-enquiry notice.

## Request, response and state

The button calls `handleGetVerifiedQuote` with the selected published ID, date, numeric adults and a copy of the ages. Infants are encoded as age zero using the existing pricing contract. It opens or validates an owned trip and submits `POST /api/agent?trip_id=[redacted]` via the AG-UI client. The AG-UI envelope contains a unique run ID and a user message whose content is the serialized structured action.

The historical requests and persisted responses are recorded in [redacted incident evidence](live-pricing/before-responses.redacted.json). For Case A the user message was:

```json
{"type":"REQUEST_QUOTE","payload":{"tourId":"T01","date":"2027-01-10","adults":2,"childAges":[]}}
```

The saved Case A response included an `EnquiryNotice` with text `Specialist confirmation required`, the historical UUID, and unrelated sources `T03`, `T04`, and `T02`. The SQLite trace does not retain the original HTTP status or stream framing.

The repaired graph validates the explicit action and initializes the pricing context directly. The completed AG-UI snapshot carries the parsed A2UI surface and a `PriceBreakdown` for a verified quote or a typed `EnquiryNotice` with a reason and public reference for a persisted unavailable result. Workbook import errors on explicit quote requests fail the run before enquiry creation. The existing layout displays the matching result, an outdated quote after an input edit, a validation message, or a retryable error. Tour navigation remounts the form. A configuration change aborts the current request and clears the notice, and a response must pass the current request guard before it can update the page.

Explicit quote enquiry reuse checks the owned trip and the persisted tour, date, adults, ages including infants, and outcome. Matching repeat requests reuse the enquiry and still write a quote revision. Traveller links use the saved public enquiry reference when supplied. The API retains the historical UUID lookup for older links.

## Files modified

- `apps/api/mira/agent.py` handles explicit graph routing, enquiry compatibility, public references, pricing digest and service failures.
- `apps/api/mira/catalog.py`, `apps/ceylon-compass/src/lib/live/catalog.ts` and `apps/web/lib/catalog.ts` carry the public enquiry reference on verified quotes.
- `apps/ceylon-compass/workspace/Workspace.jsx` manages the active configuration and request lifecycle in the existing tour detail.
- `scripts/dev.sh` keeps an explicit `MIRA_DB` override when the local environment file also declares a database.
- `apps/web/tests/live-pricing.spec.ts` covers the real traveller and staff paths with an isolated fixture.

## Browser captures

- [Before restart, original tour-detail bundle](live-pricing/before.png)
- [After, Sigiriya with two adults](live-pricing/sigiriya-two.png)
- [After, Sigiriya with four adults](live-pricing/sigiriya-four.png)
- [After, Colombo with six children](live-pricing/colombo-six-children.png)
- [After, a specific unavailable reason](live-pricing/unavailable.png)
- [After, mobile Sigiriya](live-pricing/sigiriya-mobile.png)

The before image shows the original page before submission. The failing turn evidence comes from the copied database, avoiding a new write to the original database.

## Verification and limits

The API suite ran with `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests` and reported 215 passed and 1 skipped. The final Chrome run of `live-pricing.spec.ts` reported 2 passed in 5.6 seconds against revision `live-pricing-repair-r4` and the isolated database. An earlier attempt encountered a workspace JavaScript chunk fetch failure after refresh and displayed the retryable error. The chunk returned HTTP 200 on recheck, and the final run passed on the same revision.

The Playwright suite checks browser requests and A2UI snapshots, exact prices, staff calculation and digest parity, stale response cancellation, input and tour transitions, compatible refresh, public enquiry lookup, repeat requests, and desktop and mobile rendering. The mobile check includes viewport overflow and the verified quote region. Screenshot comparison was visual.

Acceptance covers the local development stack started with the documented command. The stack is running with the isolated acceptance database. No hosted deployment was part of this verification. The original browser profile, old HTTP status and a pre-repair screenshot after submission were unavailable. The old and current displayed results are evidenced by the saved pre-repair turns and real browser captures of the repaired stack.

# Mira Local MCP Integration & Verification

**Server:** `apps/web/mcp/server.mjs` (`mira-travel` v1.1.0, `@modelcontextprotocol/sdk` `StdioServerTransport`)  
**Standalone Smoke Test:** `make mcp-smoke` (`./scripts/test-mcp.sh` → `apps/web/mcp/smoke.mjs`)  
**Machine-Readable Report:** `evals/report/mcp_smoke.json`

---

## 1. Architecture (Single Business Authority)

```text
  MCP Client (SDK StdioClientTransport)
       │
       │  JSON-RPC over stdio (search_tours, get_quote, create_enquiry,
       │                       list_destinations, get_tour_details, get_enquiry_status)
       ▼
  apps/web/mcp/server.mjs  (stateless input validation + visitor cookie jar)
       │
       │  HTTP / SSE (mira_session cookie, no duplicated pricing/filtering)
       ▼
  FastAPI Backend (apps/api/mira/main.py)
       ├─▶ GET  /api/tours, /api/guide, /api/sources/{id}   (published-only catalogue)
       ├─▶ POST /api/session                                (isolated visitor session)
       ├─▶ POST /api/agent                                  (LangGraph + Decimal workbook pricing)
       └─▶ GET  /api/enquiries/{ref}                        (session-owned enquiry status)
```

All pricing, rate validation, published-content grounding, and enquiry persistence remain exclusively inside FastAPI + `mira.data.price()` (`rate_sheet_2026-27.xlsx`).

---

## 2. Supported MCP Tools

| Tool | Read-Only | Purpose & Authority |
|---|---|---|
| `search_tours` | Yes | Searches `GET /api/tours` by title, category, start, or destination (published tours only; excludes drafts `C-*` and `T15`). |
| `get_quote` | No | Validates `tour`, calendar `date`, `adults`, `child_ages`; calls `@trip` via `/api/agent` to issue deterministic USD quote + `public_reference` (`ENQ-...`) or fail-closed `specialist_required` with `reason_code`. |
| `create_enquiry` | No | Saves a non-priced custom journey enquiry (`destinations`, `days`, `adults`, optional `date`) via `/api/agent`, returning `public_reference` and `reason_code`. |
| `list_destinations` | Yes | Lists published Sri Lanka destinations from `GET /api/guide`. |
| `get_tour_details` | Yes | Returns grounded published tour details and `source` reference via `GET /api/sources/{tour}`. |
| `get_enquiry_status` | Yes | Retrieves enquiry status via `GET /api/enquiries/{reference}` strictly scoped to the MCP client's active `mira_session` cookie (`404` / `unavailable` for other sessions). |

---

## 3. Input & Output Schemas (Core Tools)

- **`search_tours`:** `{ query?: string (max 100) }` → `{ tours: [{ id, title, category, duration, start, destinations, summary }] }`
- **`get_quote`:** `{ tour: /^[A-Z][A-Z0-9-]{1,60}$/, date: ISO YYYY-MM-DD, adults: int 1..100, child_ages: int[] (0..120, max 30) }`
  - Verified response: `{ status: "verified", quote: { id, source, title, date, adults, ages, currency: "USD", total, deposit, balance, validity }, enquiry, public_reference }`
  - Unavailable/expired response: `{ status: "specialist_required", enquiry, public_reference, reason_code, tour_id, message }`
  - Invalid/unknown responses: `{ status: "invalid_input" | "unknown_tour", message }` (or MCP `-32602` schema error)
- **`create_enquiry`:** `{ destinations: enum[...](1..6), days: int 1..90, adults: int 1..100, date?: ISO YYYY-MM-DD }`
  - Response: `{ status: "saved", enquiry, public_reference, reason_code, message }`

---

## 4. Session & Privacy Boundaries

- **Financial Privacy:** `get_quote`, `create_enquiry`, and `get_enquiry_status` never return `cost_lkr`, `gross_profit_pct`, `hotel_rows`, or private staff notes.
- **Session Isolation:** Each MCP stdio process establishes its own `mira_session` cookie via `POST /api/session`. `GET /api/enquiries/{reference}` enforces `t.visitor = ?` ownership so an unrelated MCP client cannot look up another session's enquiry even if it knows the `ENQ-...` reference.

---

## 5. Standalone Startup & Verification

```sh
# Self-contained smoke test (starts isolated temp SQLite + FastAPI, runs MCP-01..MCP-10, cleans up)
make mcp-smoke
```

### Observed Verification Results (`evals/report/mcp_smoke.json`)

| ID | Scenario | Outcome | Verified Evidence |
|---|---|---|---|
| `MCP-01` | Tool discovery | **PASS** | `create_enquiry`, `get_enquiry_status`, `get_quote`, `get_tour_details`, `list_destinations`, `search_tours` |
| `MCP-02` | Published catalogue search (`sigiriya`) | **PASS** | Returned `T01`; excluded unpublished drafts (`T15`, `C-*`) |
| `MCP-03` | Verified day-tour quote (`T01`, 2 adults, `2027-01-10`) | **PASS** | `USD 315` total, `USD 315` deposit, `USD 0` balance, `ENQ-...` |
| `MCP-04` | Verified multi-day quote (`T09`, 2 adults, `2027-05-03`) | **PASS** | `USD 2,125` total, `USD 532` deposit, `USD 1,593` balance |
| `MCP-05` | Family reconciliation (`T09`, 2 adults + `[7, 10]`, `2027-04-12`) | **PASS** | `USD 2,965` total, `USD 742` deposit, `USD 2,223` balance (matches workbook & `S03`; `Q-1043` discrepancy preserved) |
| `MCP-06` | Expired rates (`T01`, `2027-11-01`) | **PASS** | `status: "specialist_required"`, `reason_code: "date_or_fx_expired"`, `ENQ-...`, zero invented price |
| `MCP-07` | Custom 10-day family enquiry (Kandy & Ella) | **PASS** | Persisted `ENQ-...`, retrievable via `get_enquiry_status` in same session |
| `MCP-08` | Financial privacy | **PASS** | Zero `cost_lkr`, `gross_profit_pct`, `margin`, or `hotel_rows` in responses |
| `MCP-09` | Invalid inputs (`2027-02-31`, `T99`, `adults=0`, `age=150`) | **PASS** | Graceful MCP `-32602` / `unknown_tour` structured rejections |
| `MCP-10` | Cross-client session isolation | **PASS** | Second independent MCP client received `status: "unavailable"` for primary session's `ENQ-...` |

---

## 6. Compatible Desktop Client Configuration (Example)

Example stdio configuration for MCP-compatible desktop clients (note: verified end-to-end via `@modelcontextprotocol/sdk` `StdioClientTransport` in `make mcp-smoke`; external desktop GUIs such as Claude Desktop or Cursor were **not** separately launched during verification):

```json
{
  "mcpServers": {
    "mira-travel": {
      "command": "node",
      "args": ["/ABS/PATH/TO/apps/web/mcp/server.mjs"],
      "env": {
        "MIRA_API_URL": "http://127.0.0.1:8000"
      }
    }
  }
}
```

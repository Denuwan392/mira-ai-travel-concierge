# Staff and Admin Portal — Deep Technical Audit

**Date:** 25 November 2026  
**Auditor Roles:** Principal Software Architect, Application Security Auditor, Full-Stack Engineer  
**Component:** Staff Portal, Authentication, Dashboard Metrics, Enquiry Follow-Up, Quotation Finance, AI Content Studio, Audit Trail

---

## 1. Executive Summary: The "Two Staff Portals" Disconnect

The audit reveals a **critical disconnect between the frontend routes in the repository**:

```
               ┌────────────────────────────────────────────────────────┐
               │ Primary User Entry: http://127.0.0.1:5175/dump.html    │
               │ (apps/ceylon-compass/workspace/Workspace.jsx)          │
               └──────────────────────────┬─────────────────────────────┘
                                          │
                         User clicks "Staff" in nav/footer
                                          │
                                          ▼
     ┌────────────────────────────────────────────────────────────────────────┐
     │ Workspace.jsx Internal Route: case '/staff'                            │
     │ -> Renders StaffPage (Workspace.jsx lines 4337-4527)                   │
     │                                                                        │
     │  CRITICAL DEFECTS:                                                    │
     │  • Dashboard cards check WRONG KEYS -> falls back to hardcoded 5, 3, 54│
     │  • Enquiry table is read-only (no click, no notes, no status update)   │
     │  • When table empty, displays hardcoded mock row: ENQ-M5K2X / James W. │
     │  • Content Studio / Drafts tab is 100% MISSING (commented out in code) │
     │  • Admin User Management tab is 100% MISSING                           │
     │  • Audit Trail tab is 100% MISSING                                     │
     │  • Financial breakdown / Gross profit % is 100% MISSING                │
     └────────────────────────────────────────────────────────────────────────┘

     ┌────────────────────────────────────────────────────────────────────────┐
     │ Meanwhile, at apps/ceylon-compass/src/routes/staff.tsx (1,018 LOC):    │
     │                                                                        │
     │  FULLY IMPLEMENTED BUT UNCONNECTED TO WORKSPACE:                       │
     │  • Correct overview keys matching backend /api/staff/dashboard/overview│
     │  • Full enquiry management with status updates, notes & staff assign   │
     │  • Internal financial breakdown (buy cost, gross profit %, margin)     │
     │  • Full execution trace event viewer with millisecond stage timings    │
     │  • AI Content Studio with draft creation, review notes, & publish gate │
     │  • Admin User Management (role changes, deactivation)                  │
     │  • Immutable append-only audit trail viewer                            │
     └────────────────────────────────────────────────────────────────────────┘
```

Because an evaluator or examiner runs `make dev` and opens `http://127.0.0.1:5175/dump.html` (the primary integrated workspace), clicking "Staff" loads the **incomplete prototype** inside `Workspace.jsx`. This creates the false impression that the staff portal was barely started, even though complete backend APIs and a complete TanStack Start page (`src/routes/staff.tsx`) already exist in the repository.

---

## 2. Authentication & Authorization Audit

### 2.1 Backend Enforcement vs Frontend Simulation
- **Enforcement Mechanism:** Authentication is **strictly enforced server-side** by FastAPI dependencies in `apps/api/mira/auth.py` and `apps/api/mira/main.py`.
- **Password Security:** Passwords are hashed using standard **Argon2id** (`mira.auth:hash_password`) with 64 MB memory cost, 2 iterations, 4 lanes, and 16-byte cryptographically secure salts (`os.urandom`). Password verification runs in constant time.
- **Session Tokens:** Session identifiers are generated using `secrets.token_urlsafe(32)` and persisted in SQLite `user_sessions`.
- **Cookie Security:** Cookies (`mira_auth`) are issued with `HttpOnly=True`, `SameSite=Lax`, and `Path="/"`. When `MIRA_SECURE_COOKIE=1`, `Secure=True` is enforced.
- **Brute-Force Rate Limiting:** `mira.auth:check_brute_force` and `record_failed_login` track failed login attempts per key (email or IP) in `login_attempts`. Five failed attempts trigger an immediate `429 Too Many Requests` lockout for 15 minutes (900 seconds).

### 2.2 Roles and Role Boundaries
The system defines 5 roles in SQLite: `guest`, `traveller`, `staff`, `approver`, `admin`.
- `role()` dependency (`apps/api/mira/main.py` lines 91–128) checks session cookies against `users` and `user_sessions`.
- **RBAC Checks:**
  - `GET /api/staff/enquiries` $\to$ Requires `admin`, `approver`, or `staff`. Non-staff receive `401/403`.
  - `GET /api/staff/enquiries/{key}` $\to$ Requires `admin`, `approver`, or `staff`. Exposes internal costs and margins.
  - `POST /api/staff/drafts` $\to$ Requires `staff`, `editor`, `approver`, or `admin`.
  - `POST /api/staff/drafts/{id}/review` $\to$ **Requires `approver` strictly**.
  - `POST /api/staff/drafts/{id}/publish` $\to$ **Requires `approver` strictly**.
  - `GET /api/admin/users` $\to$ Requires `admin` strictly.
  - `PATCH /api/admin/users/{id}` $\to$ Requires `admin` strictly. Self-demotion and self-deactivation are rejected (`400 Bad Request`).

### 2.3 Verified Security Defect: Admin Publication Lockout
In `apps/api/mira/main.py` lines 923 and 946:
```python
@app.post("/api/staff/drafts/{key}/review", dependencies=[Depends(website)])
def review_draft(key: str, body: DraftReviewInput, actor: str = Depends(role)):
    if actor != "approver":
        raise HTTPException(403, "Approver access required")

@app.post("/api/staff/drafts/{key}/publish", dependencies=[Depends(website)])
def publish(key: str, actor: str = Depends(role)):
    if actor != "approver":
        raise HTTPException(403, "Approver access required")
```
- **Finding:** If the user logs in as `admin` (e.g., using `MIRA_ADMIN_EMAIL`), `actor` evaluates to `"admin"`. Because `actor != "approver"`, the system returns `403 Forbidden`!
- **Consequence:** An administrator cannot review or publish drafts unless they either promote a secondary account to `approver` and log in as that user, or use a Bearer token with `MIRA_APPROVER_TOKEN`.

---

## 3. Staff Dashboard Metrics Audit

### 3.1 Backend Implementation (`GET /api/staff/dashboard/overview`)
The backend endpoint (`main.py` lines 756–777) computes real metrics from database tables:
```python
total_enquiries = conn.execute("SELECT COUNT(*) FROM enquiries").fetchone()[0]
pending_followups = conn.execute("SELECT COUNT(*) FROM enquiries WHERE status IN ('new', 'waiting')").fetchone()[0]
quotes_requiring_confirmation = conn.execute("SELECT COUNT(*) FROM enquiries WHERE reason='verified_quote' AND status='new'").fetchone()[0]
pending_content_approvals = conn.execute("SELECT COUNT(*) FROM drafts WHERE status IN ('draft', 'revision_requested')").fetchone()[0]
recent_activity = conn.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 10").fetchall()
```
- These metrics are calculated dynamically from SQLite and update immediately upon data changes.

### 3.2 Frontend Defect in `Workspace.jsx` (Lines 4441–4453)
```javascript
<div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
  {[
    { label: 'Open enquiries', value: overview?.open_enquiries ?? enquiries.length, color: 'brand-orange' },
    { label: 'Pending quotes', value: overview?.pending_quotes ?? '5', color: 'brand-sun' },
    { label: 'Draft content', value: overview?.drafts ?? '3', color: 'brand-teal' },
    { label: 'Evaluations', value: overview?.evaluations ?? '54', color: 'brand-leaf' },
  ].map(stat => (
    <Card key={stat.label} className="p-5">
      <p className="text-xs text-text-muted mb-1">{stat.label}</p>
      <p className={`text-xl font-bold text-${stat.color}`}>{stat.value}</p>
    </Card>
  ))}
</div>
```
- **Evidence of Defect:**
  - `overview.open_enquiries` is undefined $\to$ falls back to `enquiries.length`.
  - `overview.pending_quotes` is undefined $\to$ falls back to hardcoded string `'5'`.
  - `overview.drafts` is undefined $\to$ falls back to hardcoded string `'3'`.
  - `overview.evaluations` is undefined $\to$ falls back to hardcoded string `'54'`.
- **Verdict:** **Confirmed High Severity UI Defect**. Evaluators inspecting the workspace see hardcoded demonstration numbers.

---

## 4. Enquiry Management Audit

### 4.1 Full Lifecycle Verification
The full business lifecycle was tested end-to-end via API:
1. **Creation:** A quote or custom/missing rate turn triggers `save()` in `agent.py`. Rows are inserted into `quotes` and `enquiries` with `id`, `trace`, `quote`, `trip`, `reason`, `status='new'`.
2. **Staff Read:** Staff queries `GET /api/staff/enquiries`. Returns all active enquiries. Filterable by `status`, `assigned_to`, and `search`.
3. **Staff Detail View:** Staff queries `GET /api/staff/enquiries/{key}`. Returns enquiry record, linked trace stages, financial buy costs/margins, and internal notes history.
4. **Follow-Up Update:** Staff calls `PATCH /api/staff/enquiries/{key}` with `status`, `note`, and `assigned_to`.
   - SQLite updates `enquiries.status`, `assigned_to`, `assigned_name`, `updated_at`.
   - Inserts note into `notes` table with `actor`, `body`, `created`.
   - Inserts event into `audit` table.
5. **Traveller Status Check:** Traveller queries `GET /api/enquiries/{reference}`. Returns updated status (`contacted`, `waiting`, `closed`). Scoped strictly to the traveller's visitor session cookie.

### 4.2 Frontend Comparison

| Feature | `Workspace.jsx` (`StaffPage`) | `src/routes/staff.tsx` |
|---|---|---|
| Enquiry Table Listing | Yes (4 columns) | Yes (7 columns with badges) |
| Search by Reference/Keyword | **No** (Missing) | **Yes** (`input` with live query) |
| Filter by Status | **No** (Missing) | **Yes** (Dropdown filter) |
| Filter by Assigned Staff | **No** (Missing) | **Yes** (Dropdown filter) |
| Click Row to View Details | **No** (Non-interactive) | **Yes** (`setSelectedEnquiry`) |
| View Financial Breakdown | **No** (Missing) | **Yes** (Cost LKR, Margin %, Deposit) |
| View Execution Trace Events | **No** (Missing) | **Yes** (Stages & latencies) |
| Update Status (`new` $\to$ `contacted`) | **No** (Missing) | **Yes** (`PATCH /api/staff/enquiries/{id}`) |
| Add Internal Staff Note | **No** (Missing) | **Yes** (Note input with PII check) |
| Assign to Staff Member | **No** (Missing) | **Yes** (`GET /api/staff/users/assignable`) |
| Empty State Handling | Displays **fake mock row**: `ENQ-M5K2X` | Displays "No enquiries matching current filters" |

---

## 5. Staff Quotation Management Audit

### 5.1 Financial Visibility and Privacy Boundary
The assignment strictly requires:
> *"Each quote stores its cost, price and gross-profit % for staff; travellers see only the price and deposit, never costs or margins."*

| Data Field | Traveller (`/api/quotes`) | Staff (`/api/staff/enquiries/{id}`) | Compliance Status |
|---|---|---|---|
| Tour Title & Slug | Visible (`title`, `source`) | Visible (`trip.title`) | **Pass** |
| Travel Date & Party | Visible (`date`, `adults`, `ages`) | Visible (`trip.date`, `adults`, `ages`) | **Pass** |
| Quoted Selling Price | Visible (`total`) | Visible (`finance.total`) | **Pass** |
| Deposit Required | Visible (`deposit`) | Visible (`finance.deposit`) | **Pass** |
| Total Buy Cost (LKR) | **REDACTED / ABSENT** | Visible (`finance.cost_lkr`) | **Pass** |
| Gross Profit % | **REDACTED / ABSENT** | Visible (`finance.gross_profit_pct`) | **Pass** |
| Cost Breakdown (Guide, Van, Hotels) | **REDACTED / ABSENT** | Visible (`finance.breakdown`) | **Pass** |
| Execution Trace ID | Visible (`trace`) | Visible (`trace`) | **Pass** |

---

## 6. AI-Generated Content Management Audit

### 6.1 Workflow Verification
1. **Command Generation:** An authenticated editor/staff posts command `POST /api/staff/drafts` (`"Prepare a 5-day Hill Country journey concept using Ella materials"`).
   - In local mode: Extractive generator parses destination content for "Ella", extracts evidence, constructs draft.
   - In Gemini mode: Invokes `generate_structured(DraftText, ...)` with prompt forbidding invented dates/prices.
   - Inserts record into `drafts` with `status = 'draft'`.
2. **Draft Isolation:** Draft records have `status = 'draft'`.
   - `published_records()` in `apps/api/mira/store.py` only joins drafts where `status = 'published'`.
   - Public source endpoint `GET /api/sources/{id}` returns `404 Not Found`.
   - Mira RAG retrieval in `agent.py:retrieve()` never encounters or returns the draft.
3. **Approval Gate:**
   - Non-approvers attempting `POST /api/staff/drafts/{id}/publish` receive `403 Forbidden`.
   - An Approver posts `POST /api/staff/drafts/{id}/publish`.
   - Database updates `status = 'published'` and `published = CURRENT_TIMESTAMP`.
4. **Publication & Retrieval:**
   - `published_records()` immediately reflects the published draft.
   - `GET /api/sources/{id}` returns `200 OK`.
   - Mira answers prompts referencing the new title and provides the source citation.

### 6.2 Frontend Defect in `Workspace.jsx`
- In `Workspace.jsx`, line 4345 defines `const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'enquiries' | 'drafts'`.
- However, lines 4455–4470 **only render buttons for 'enquiries' and 'overview'**. The 'drafts' tab is completely omitted from the UI.
- Consequently, evaluators using `Workspace.jsx` cannot test the content approval workflow from the UI.
- In contrast, `src/routes/staff.tsx` renders a complete **Content Studio** tab with draft creation prompt, drafts table, reviewer notes, status badges, and Approve/Publish action buttons.

---

## 7. Evaluation & Tracing Dashboard Audit

1. **Evaluation Endpoint (`GET /api/staff/evaluation`):**
   - Returns real test output from `evals/report/report.json`.
   - Contains total cases ($54$), passed ($53$), failed ($1$), pass rate ($98.1\%$), and categorized breakdowns across 9 requirements.
   - Includes real snapshot of failed case $P03$ with full stage execution trace.
2. **Trace Endpoint (`GET /api/staff/traces/{trace}`):**
   - Queries `traces` and `failed_traces` tables in SQLite.
   - Returns JSON stage events: `interpret`, `retrieval`, `pricing`, `validated_ui`, `mock_booking`, `persistence`.
3. **Frontend Integration in `Workspace.jsx`:**
   - `Workspace.jsx` line 4430 renders an `<a>` tag linking to `/api/staff/evaluation`.
   - While functional, it opens raw JSON in a new browser tab rather than rendering a visual evaluation dashboard.
   - `src/routes/staff.tsx` also links out to the evaluation endpoint.

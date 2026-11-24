# Ceylon Compass Holidays — Mira AI Demo Checklist

## 1. Pre-Demo Setup
1. Ensure `.env` has `MIRA_ADMIN_EMAIL` and `MIRA_ADMIN_PASSWORD` configured before first startup (or use the seeded admin credentials).
2. Optional: configure `GEMINI_API_KEY` + `GEMINI_MODEL` for live LLM suggestions/drafts and `LANGFUSE_*` for external tracing. Without keys, Mira runs deterministically using local rules, extractive drafts, and SQLite trace storage.
3. Start the full stack:
   ```sh
   make dev
   ```
4. Verify services are listening:
   - **Preferred Travel Workspace:** `http://127.0.0.1:5175/dump.html` (or `/workspace/index.html`)
   - **Unified Staff Console:** `http://127.0.0.1:5175/staff` (and `http://127.0.0.1:5175/workspace/index.html#/staff`)
   - **FastAPI Health & OpenAPI:** `http://127.0.0.1:8000/api/health` and `http://127.0.0.1:8000/docs`

## 2. Traveller Journey Walkthrough
1. **Homepage Prompt Forwarding:** On `http://127.0.0.1:5175/dump.html`, enter `"Sigiriya day trip for two adults on 10 January 2027"` (or click a quick chip) → verify navigation to `/mira` and automatic first-turn submission.
2. **Deterministic Quote & Infants:** Ask `"Sigiriya day trip for 2 adults and 1 infant on 10 January 2027"` → verify deterministic workbook price matches 2 adults (zero infant surcharge).
3. **Child Age Prompting:** On a Tour Detail page, increment children → verify per-child age inputs and infant stepper; verify quote invalidation (`Quote Outdated` → `Recalculate quote`) when party size or date changes.
4. **Mock Booking Simulation:** Run `"declined"` or `"expired"` then `"success"` → verify confirmed booking reference (`confirmed_reference`) is preserved even if a later simulation fails.
5. **Contact Enquiry & Profile:** Submit a booking/custom enquiry with email/phone → verify `/enquiry/{reference}` renders real status (and unknown references render `"Enquiry not found"`). Open `/profile` to inspect saved journeys, recent quotations, and active enquiries.

## 3. Staff & Approver Governance Walkthrough
1. Sign in at `http://127.0.0.1:5175/staff` as **Admin**.
2. **Overview:** Confirm live DB counts (`open_enquiries`, `total_enquiries`, `pending_followups`, `contactable_enquiries`, `pending_content_approvals`) and the embedded Visual Evaluation Suite summary (`53/54`).
3. **Enquiries CRM:** Filter/search enquiries, open an enquiry detail drawer, inspect **Traveller Information**, **Internal Finance** (`cost_lkr`, `gross_profit_pct`), **Quotation Revisions**, **Trace**, and save a status + assignee + follow-up deadline + note.
4. **Role & Content Governance:** In **Users**, promote a demo account to `approver`. Note that `admin` cannot publish drafts (`403`); sign in as `editor` to create a draft, then sign in as `approver` to review and publish it, and verify Mira retrieves the published content in chat.

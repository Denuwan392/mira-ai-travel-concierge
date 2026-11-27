# Mira — Live Coding Playbook (15+ Safe Modification Exercises)

> [!IMPORTANT]
> **Do not edit the submitted `main` branch during practice.** Create an isolated copy or git worktree first:
> ```sh
> git worktree add /tmp/mira-practice HEAD
> cd /tmp/mira-practice
> ```
> When finished, remove it cleanly with `git worktree remove /tmp/mira-practice`.

---

## Top 5 Highest-Probability Exercises (Step-by-Step Practice)

### Exercise 1: Change the Multi-Day Gross Margin (e.g., 25% → 30%)
- **Difficulty:** Easy · **Likelihood:** **HIGH**
- **Where:** `GenAI-Intern-Take-Home-Assignment/ceylon-compass-dataset/rates/rate_sheet_2026-27.xlsx` (`Settings` tab, row `"Margin – multi-day tours"`) **and** `apps/api/mira/data.py:310-315` (`calculate`).
- **Existing Code (`apps/api/mira/data.py:310-315`):**
  ```python
  margin = number(settings["Margin – day tours" if kind == "Day tour" else "Margin – multi-day tours"])
  deposit_fraction = number(settings["Deposit – multi-day tours"])
  step = number(settings["Round booking total up to next (USD)"])
  if cost <= 0 or fx <= 0 or not 0 <= margin < 1 or not 0 < deposit_fraction <= 1 or step != 5:
      raise Unavailable("invalid_settings")
  sell = round_up(cost / (fx * (1 - margin)), step)
  ```
- **Step-by-Step Practice (Code Override for Interview Demo):**
  If asked to override multi-day margin in Python (e.g., to `0.30` instead of reading `0.25` from Excel):
  1. Open `apps/api/mira/data.py` at line 310.
  2. Replace:
     ```python
     margin = Decimal("0.30") if kind != "Day tour" else number(settings["Margin – day tours"])
     ```
  3. **Math check (Q-1042, T09, 2 adults):** `cost_lkr = 477,500`, `fx = 300`. Previously `477500 / (300 * 0.75) = 2122.22 -> 2125`. At `30%` margin: `477500 / (300 * 0.70) = 2273.81 -> 2275`.
  4. **Verify:** `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_pricing.py` (expect `Q1042`, `Q1043`, `Q1044` to fail with the new higher totals, proving the change took effect; `Q1041` day tour stays `315`).
  5. **Undo:** `git checkout -- apps/api/mira/data.py` (or `rate_snapshots` cache stays unaffected because `calculate` runs on `Rates`).

---

### Exercise 2: Change the Multi-Day Deposit Rule (e.g., 25% → 30%, or 30-day window → 45 days)
- **Difficulty:** Easy · **Likelihood:** **HIGH**
- **Where:** `apps/api/mira/data.py:311, 316-317` (`calculate`) and Excel `Settings` tab.
- **Existing Code (`apps/api/mira/data.py:311, 316-317`):**
  ```python
  deposit_fraction = number(settings["Deposit – multi-day tours"])
  ...
  due = number(settings["Full payment if starting within (days)"])
  deposit = sell if kind == "Day tour" or (start - today).days <= due else round_up(sell * deposit_fraction, 1)
  ```
- **Step-by-Step Practice:**
  1. To change deposit to 30% in code: `deposit_fraction = Decimal("0.30")`.
  2. To change full-payment window to 45 days: `due = Decimal("45")`.
  3. **Expected Result:** For `Q-1043` (`sell = 2965`), `round_up(2965 * 0.30, 1) = ceil(889.5) = 890` (was `742`). Balance = `2965 - 890 = 2075`.
  4. **Verify:** `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_pricing.py -k "full_payment or exact_quote"`.
  5. **Regression Risk:** Existing saved quotes in SQLite `quotes` table keep their historical `public` JSON, but `quote_current` in `main.py` recalculates and will flag older quotes as stale if deposit changes? Note: `quote_current` compares `total`, `deposit`, `balance` — check `main.py:251-261`.
  6. **Undo:** `git checkout -- apps/api/mira/data.py`.

---

### Exercise 3: Adjust Child Pricing Rule (e.g., Child Meals 50% → 75%, or Child Age Cutoff 12 → 10)
- **Difficulty:** Medium · **Likelihood:** **HIGH**
- **Where:** `apps/api/mira/data.py:248-249, 306` (`calculate`).
- **Existing Code (`apps/api/mira/data.py:248-249, 306`):**
  ```python
  adults += sum(age >= 12 for age in ages)
  children = sum(2 <= age <= 11 for age in ages)
  ...
  "meals": number(meals) * (adults + Decimal(children) / 2) * days,
  ```
- **Step-by-Step Practice:**
  1. To raise child meals from 50% to 75%:
     ```python
     "meals": number(meals) * (adults + Decimal(children) * Decimal("0.75")) * days,
     ```
  2. **Expected Result (T01, 2 adults + 1 child age 7):** Meal cost increases by `0.25 * meals * 1 day`.
  3. **Verify:** `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_pricing.py -k "age_boundaries or exact_quote"`.
  4. **Undo:** `git checkout -- apps/api/mira/data.py`.

---

### Exercise 4: Customize Missing-Rate / Expired-FX Response Copy
- **Difficulty:** Easy · **Likelihood:** **HIGH**
- **Where:** `apps/api/mira/agent_workflow/compose.py:78-124` (`_compose_unavailable_quote`, called by `compose`).
- **Existing Behavior:** When `quote_node` (`agent_workflow/quote.py:15-43`) catches `Unavailable(reason)`, it stores `w["reason"] = str(exc)`, and `_compose_unavailable_quote` emits an `EnquiryNotice` with `outcome="PRICE_UNAVAILABLE"` and `reason_code=reason` plus a polite specialist-handoff message without any invented dollar amount.
- **Step-by-Step Practice:**
  1. Locate `_compose_unavailable_quote` in `apps/api/mira/agent_workflow/compose.py` (`lines 78-124`).
  2. Add a specific friendly message when `reason == "date_or_fx_expired"` (e.g. `"Live rates are currently fixed through 30 Sep 2027; our specialists will prepare a custom quote for your dates."`).
  3. **Verify:** `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_workflows.py -k "expired or missing"` and check `Turn` validation still passes (no `<` or `>`, max 6000 chars, no `PriceBreakdown`).
  4. **Undo:** `git checkout -- apps/api/mira/agent_workflow/compose.py`.

---

### Exercise 5: Enforce Separate Approver Sign-Off Before Publishing Drafts
- **Difficulty:** Medium · **Likelihood:** **MEDIUM–HIGH**
- **Where:** `apps/api/mira/main.py:1630-1643` (`publish`).
- **Existing Behavior:** `publish()` currently checks that the caller is `approver` or `admin` (via `role`), and updates `drafts` to `status='published'` even if `status` was `'draft'` (direct publish without intermediate `'approved'` state).
- **Proposed Modification:** Require `row["status"] == "approved"` before `publish()` can transition a draft to `'published'` (returning `409 Conflict` if still `'draft'`).
- **Verify:** `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_auth_rbac.py apps/api/tests/test_workflows.py`.
- **Undo:** `git checkout -- apps/api/mira/main.py`.

---

## Additional Exercises (6–15)

| # | Reviewer Request | Difficulty | Likelihood | File & Function | Exact Change & Verification |
| :---: | :--- | :---: | :---: | :--- | :--- |
| **6** | Switch configured Gemini model | Easy | High | `.env` (`GEMINI_MODEL`) & `provider.py:51` | Update `GEMINI_MODEL=gemini-2.5-flash` (or `gemini-3.5-flash-lite`) and restart API. Verify `gemini.completed` in logs. |
| **7** | Prefer closest duration in tour suggestions | Medium | Medium | `apps/api/mira/search.py:183-215` (`rank_filtered_tours`) | Adjust `score(tour_id)` tuple weights to prioritize `day_diff` ahead of `theme_bonus`. Verify with `test_tour_relevance_regression.py`. |
| **8** | Recognize additional dietary keywords (e.g., `"gluten-free"`, `"nut allergy"`) | Easy | Medium | `apps/api/mira/agent_workflow/interpret.py` (`_classify_intent`) | Extend the dietary regex in `_classify_intent()` to include `gluten[- ]?free|allerg`. Verify with `test_workflows.py`. |
| **9** | Add a new deterministic evaluation case | Easy | High | `evals/cases/authored.jsonl` | Append one JSONL line with `id`, `origin`, `category`, `turns`, `expected`. Run `PYTHONPATH=apps/api .venv/bin/python evals/runner.py` in a temp copy. |
| **10** | Relabel the canonical quote panel (e.g., `"Deposit Due Today"` → `"Advance Deposit"`) | Easy | High | `apps/ceylon-compass/workspace/Workspace.jsx:3034+` (`PriceBreakdownPanel`) | Edit the JSX label text, rebuild (`npm --prefix apps/ceylon-compass run workspace:build`), and run `npm --prefix apps/ceylon-compass test`. |
| **11** | Tighten max source citations per turn (`6` → `3`) | Easy | Low | `apps/api/mira/catalog.py:156` (`Turn.sources`) | Change `Field(max_length=6)` to `Field(max_length=3)` and clamp `sources[:3]` in `compose()`. Run `test_ui_regression.py`. |
| **12** | Show fewer destination tour matches (`3` → `2`) | Easy | Low | `apps/api/mira/agent_workflow/retrieve.py:35-37` (`retrieve`) | Slice destination tour matches `[:2]` instead of `[:3]`. Run `test_tour_relevance_regression.py`. |
| **13** | Shorten remembered visitor cookie lifetime | Easy | Low | `apps/api/mira/main.py` (`session`) | Reduce `max_age` on `mira_session` cookie (e.g., `30 * 86400` → `7 * 86400`). Run `test_workflows.py`. |
| **14** | Shorten frontend AG-UI request timeout (`65s` → `30s`) | Easy | Low | `apps/ceylon-compass/workspace/useConversation.js:57` (`send`) | Change `65000` to `30000`. Rebuild workspace and run `npm --prefix apps/ceylon-compass test`. |
| **15** | Add `action` & `tour_id` to `pricing.completed` log event | Easy | Medium | `apps/api/mira/agent_workflow/quote.py:41-42` (`quote_node`) | Add extra keyword metadata to `event("PRICING", "pricing.completed", ...)` (never log `cost_lkr`!). Verify with `test_observability.py`. |

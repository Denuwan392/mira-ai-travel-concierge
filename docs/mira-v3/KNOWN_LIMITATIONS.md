# Known Limitations & Engineering Opportunities

While Mira v3 satisfies all employer requirements and maintains high data fidelity, the following architectural boundaries and opportunities for future enhancement are documented in the spirit of engineering transparency.

---

## 1. Known Architectural Boundaries

1. **Custom Itinerary Dynamic Pricing (Bespoke Quotation)**:
   - *Current State*: Custom multi-day routes planned through the Notebook interface do not compute instant real-time quotes; they withhold automated pricing and create a specialist `EnquiryNotice`.
   - *Rationale*: The canonical employer rate workbook (`rate_sheet_2026-27.xlsx`) only provides tabular per-person rates for predefined packages (T01–T09) and raw room sheets. Fabricating blended vehicle mileage or unverified hotel contracts without human confirmation violates financial safety.
   - *Future Enhancement*: Implement a dynamic routing cost estimator that calculates point-to-point Google Maps / OSRM driving distances, driver overnight allowances, and live hotel room inventory queries.

2. **Evaluation Metric Calibration on P03**:
   - *Current State*: The evaluation runner scores 48 / 49 (98.0%) because case P03 checks against historical quote email text ($2,680) rather than workbook logic ($2,965).
   - *Rationale*: Mira deliberately preserves deterministic adherence to the official rate workbook and Policy P03 (extra beds) rather than artificially hardcoding an exception to achieve an unearned 100% eval score.

3. **Multi-Currency Live FX Rates**:
   - *Current State*: Currency conversions (LKR to USD) use the fixed benchmark rate defined in `rate_sheet_2026-27.xlsx` (`Settings` worksheet: 225 LKR / USD).
   - *Future Enhancement*: Connect a live central bank API (e.g. Central Bank of Sri Lanka CBSL exchange rate feeds) with configurable hedging buffers.

4. **Offline Fallback for Gemini Live Sessions**:
   - *Current State*: When live Gemini API keys are absent or rate-limited, Mira gracefully falls back to deterministic local rule-based intent parsing and grounded RAG retrieval, guaranteeing 100% uptime.
   - *Future Enhancement*: Cache embedding vectors locally using ChromaDB or FAISS for offline vector similarity ranking when running without cloud LLM endpoints.

---

## 2. Frontend Operational Boundaries

1. **Staff Console (`apps/web`) Independence**:
   - The primary traveller-facing application is exclusively `apps/ceylon-compass/` (TanStack Start).
   - `apps/web/` is an internal Next.js admin prototype used for viewing raw enquiries and trace logs. It is decoupled from the public booking journey.

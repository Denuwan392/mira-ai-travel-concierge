# A2UI Architecture & Generative UI Surfaces

This document describes the Generative UI architecture implemented across Mira v3, including component catalogs, server-driven rendering via AG-UI, LLM UI planning, schema validation, and graceful fallbacks.

---

## 1. Architectural Philosophy: Constrained Generative UI

Generative UI in Mira v3 does not permit the LLM to emit arbitrary, unsafe raw HTML or unvalidated JSX. Instead, Mira employs the **A2UI (Agent-to-UI)** constrained component paradigm:
1. The backend maintains a strict, strongly-typed component catalog backed by Pydantic schemas.
2. The agent determines semantic intent and calls `plan_ui()` (`apps/api/mira/provider.py`) or rule-based composers to assemble a sequence of typed component payloads.
3. Every component payload is validated against its schema prior to serialization.
4. Validated components are streamed over Server-Sent Events (SSE) via the AG-UI protocol (`RUN_FINISHED`, `STATE_SNAPSHOT`).
5. The TanStack Start React 19 frontend (`apps/ceylon-compass/`) consumes the events and dynamically mounts high-fidelity UI elements into the `LiveCanvas` workspace.

---

## 2. Component Catalog Matrix

| Component | Pydantic Schema | Props & Attributes | Frontend Renderer (`apps/ceylon-compass`) | Fallback Behavior |
|-----------|-----------------|--------------------|--------------------------------------------|-------------------|
| **TourCard** | `TourCardProps` | `id`, `title`, `duration`, `price_usd`, `image_url`, `summary`, `tags`, `rating` | `apps/ceylon-compass/src/components/mira/TourCard.tsx` | Markdown summary card with link |
| **ItineraryDay** | `ItineraryDayProps` | `day_number`, `title`, `description`, `meals`, `accommodation`, `highlights`, `tickets` | Rendered within journey timeline views | Structured Markdown section |
| **QuoteCard** | `QuoteCardProps` | `quote_id`, `tour_id`, `tour_title`, `party`, `total_usd`, `deposit_usd`, `deposit_percentage`, `expires_at`, `status` | Direct booking card with payment action | Plain text price breakdown |
| **EnquiryNotice** | `EnquiryNoticeProps` | `trip_id`, `destination_names`, `party`, `reason`, `message`, `reference_code` | Specialist booking CTA & enquiry modal trigger | Text advice to contact specialist |
| **DestinationCard** | `DestinationCardProps` | `id`, `name`, `province`, `hero_image`, `description`, `top_attractions` | Visual destination pill with preview image | Markdown destination bullet |
| **SourceDisclosure**| `SourceDisclosureProps` | `sources`: list of `{ id, title, type, excerpt }` | Collapsible grounded citation pill list | Inline bracketed footnotes `[T01]` |

---

## 3. Streaming Event Protocol (AG-UI)

Events sent over `/api/agent` stream conform to AG-UI standards:
```json
event: RUN_STARTED
data: {"run_id": "c17377a0-...", "status": "running"}

event: STATE_SNAPSHOT
data: {
  "proposal": { "destination_ids": ["D01", "D02", "D04"] },
  "trip": { ... }
}

event: RUN_FINISHED
data: {
  "message": "Here is the day-by-day plan...",
  "components": [
    { "type": "ItineraryDay", "props": { "day_number": 1, ... } },
    { "type": "ItineraryDay", "props": { "day_number": 2, ... } }
  ],
  "sources": [
    { "id": "T09", "title": "Cultural Triangle Discovery", "type": "tour" }
  ]
}
```

---

## 4. Safety Guardrails & Validation

1. **Hard Upper Bounds**:
   - `components` count is bounded ($\le 12$) to protect client render pipelines from DOM flooding.
   - `sources` count is bounded ($\le 6$) to prevent bloated citation trees.
2. **Schema Sanitization**:
   - Components missing mandatory fields (e.g. `title` or `day_number`) fail Pydantic validation and are cleanly pruned from the payload without aborting the conversational response.
3. **Graceful Fallback**:
   - If UI component rendering encounters an unhandled runtime error on the client, `LiveCanvas` isolates the error to an ErrorBoundary and displays the assistant's structured text response with markdown tables.

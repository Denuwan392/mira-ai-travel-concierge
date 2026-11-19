# Mira trip planner review

## The demo

Open the home page, choose **Ella trip**, then **Compare these tours** in the conversation. Mira retrieves Ella's published destination note and two tours, Instafamous Sri Lanka and Treasures of Sri Lanka. The follow-up compares the same two routes. Open an earlier result from the conversation to return to its map and list. Shortlist a route using its bookmark. Shortlists last for the current planner visit.

For a dated itinerary, open **Highlights of Sri Lanka** from the planner's initial guide, choose **View itinerary**, then **Day 2**. For pricing, try **A Sigiriya day trip**, two adults, 10 January 2027. A custom ten-day Kandy and Ella family trip demonstrates the alternative specialist handoff.

[Illustrated review and ChatGPT replanning prompt](Mira-Trip-Planner-Review.pdf) · [Desktop Ella results](screenshots/after/advisor-ella-1440.jpg) · [Phone map](screenshots/after/advisor-ella-390.jpg) · [Compared journeys](screenshots/after/advisor-compare-1440.jpg) · [Day selection](screenshots/after/advisor-day-1440.jpg)

## What the recording changed

The 56-second screen recording shows a persistent conversation beside changing cards, day controls and a locator. The planner adopts that interaction. Desktop keeps conversation, results and map in sight. Phone users switch between Conversation and Journey and can open the map above the cards. An earlier response has a return-to-results action. Historical results suppress booking, quote and traveller-entry controls. The current turn owns those actions.

The four earlier visual references informed the photo-led homepage, editorial headline, floating navigation and manual photo collection. The functional interface uses the brand's Inter-first system stack. Georgia is the local editorial display face. Orange marks primary actions, forest anchors navigation and champagne supplies the focus accent. The six source photographs and map data have individual credits. [Photography and map sources](ASSET_LICENSES.md)

## Implementation

| Area | Files and responsibility |
| --- | --- |
| Baseline and capture | `docs/UI_BASELINE.md` and `docs/screenshots/{before,after}` record real Chrome workflows. Each set includes homepage, planner, quote, handoff and staff at 1440×900, 1280×800, 768×1024 and 390×844. |
| Landing and photography | `apps/web/app/page.tsx`, `layout.tsx`, `editorial.css`, `style.css` and `editorial/{hero,navigation,action,deck,atlas}.tsx` implement prompt handoff, responsive controls, manual gallery and optional WebGL. `lib/media-manifest.ts`, `public/media/licensed` and the credits route supply locally served, verified images. |
| Published data and agent | `apps/api/mira/{guide,main,agent}.py` exposes public tour destinations and actual day headings, retrieves published tours for destination questions, and keeps the previous suggestions for a comparison follow-up. Public tour text passes through the existing traveller-content filter. |
| Map and itinerary | `apps/web/lib/guide.ts` validates the public guide response. `app/plan/{guide-board,island-map,island-outline}.tsx` or `.ts` implements filtering, shortlisting, comparisons, published days and zoom. The offline map uses actual coastline and river geometry. Points indicate approximate destination centres. |
| Conversation and finance | `app/plan/{page,components}.tsx`, `plan/advisor.css` and `editorial/tour-photo.tsx` render live AG-UI turns, sources, quotes and enquiries. `app/staff/page.tsx` labels protected cost, sale, deposit and margin values. Server-side access controls remain authoritative. |
| Verification | `apps/api/tests/test_workflows.py` and `apps/web/tests/{advisor,editorial,journey,staff}.spec.ts` cover the public catalog and end-to-end journeys. |

The existing CopilotKit/AG-UI transport still carries the response. The browser validates each generated component against its Zod catalog. The map combines the validated response IDs with published place metadata. A tour without a day-by-day source shows its destinations. The map supplies geographic context and the app makes no travel-time estimates.

## Observed verification

| Check | Command or setup | Result |
| --- | --- | --- |
| Python | `make test` | 56 passed. The upstream LangGraph adapter issued 21 deprecation warnings. |
| TypeScript and production | `make lint` then `make build` | Python compilation, TypeScript and optimized Next build passed. Seven static pages generated. |
| Browser | `npm --prefix apps/web test -- --workers=1`, local Chrome with configured demo roles | 11 passed. Includes an Ella conversation, a contextual comparison, previous results, shortlist, day filter, authenticated approvals, quote, decline/retry, saved quote and mobile no-price handoff. An earlier concurrent run timed out in the booking test; isolated and sequential reruns passed. |
| Live stream | `make smoke` against the local demo | CopilotKit streamed a quote and trace ID across 23 AG-UI events. |
| Conversation eval | `PYTHONPATH=apps/api:evals .venv/bin/python` invoking `runner.run()` with a temporary report directory and the existing cases | 48/49 cases, 20/21 exact quote and deposit, 10/10 no-price, 0 unexpected quotes and 58/58 valid UI turns. |
| Accessibility | axe in Chrome, WCAG 2/2.1 A and AA tags, after opening Ella results | Zero automated violations on that state. Keyboard, narrow layouts and reduced-motion controls also exercised in browser tests. |
| WebGL and touch | Chrome with WebGL available, Chrome with context creation disabled, and a touch-enabled phone profile | Original four-way compass rendered. Without WebGL, the journey controls remained usable. Mobile tap submitted an actual prompt and reopened its results. The button border ignores pointer events; its one-shot interaction lasts 170 ms. Reduced motion disables the animation. |

[Before capture set](screenshots/before/) · [After capture set](screenshots/after/) · [Rendered compass](screenshots/after/journey-compass.png)

### Performance

Lighthouse 13.6.0 ran against a local production server using Chrome's desktop preset and default simulated mobile profile. These are single lab runs.

| Homepage profile | Performance | Accessibility | LCP | CLS | Total blocking time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Desktop | 100 | 100 | 0.7 s | 0 | 0 ms |
| Mobile | 94 | 100 | 3.1 s | 0 | 20 ms |

The initial desktop JavaScript transfer measured 155,745 bytes. Opening the optional compass added 268,578 bytes. It mounts on an explicit action, uses demand-driven rendering and unmounts while the tab is hidden. The ordinary map, chat, quote and booking flows work without it. A previous audit measured 67/53 desktop/mobile performance while other work was running. The final run followed removal of eager link prefetch and a contrast correction. The two runs cannot isolate the contribution of either change.

### Remaining gaps and next review

1. Bring simulated mobile LCP below 2.5 s. Profile the phone hero's request timing and decode cost, then compare lighter crops under the same throttling.
2. Run a live Gemini and Langfuse comparison with representative follow-ups. This demo used local discovery and SQLite traces. Measure whether free-form requests preserve the same route context and source grounding.
3. Resolve fixture P03/Q-1043 with the workbook owner. The deterministic total and deposit are USD 2,965 and USD 742. The sample expects USD 2,680 and USD 670. Preserve the workbook calculation while the inputs are reconciled.

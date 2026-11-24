# MIRA 2.0 — CINEMATIC LUXURY PRODUCT REDESIGN
## High-impact Codex execution brief for an existing, working AI travel concierge

> **INTENDED USAGE:** Paste this prompt into Codex **inside the existing Mira repository**. Also provide the four original reference screenshots in `design/references/` (or open the accompanying reference pack). This is an **implementation request, not a design brainstorming request**. Make the code changes, run the application, test flows, and capture screenshots. Preserve all validated business behavior.
>
> **RELATION TO PRIOR BRIEF:** This redesign brief **supersedes ONLY the earlier UI/art-direction sections** of `MIRA_MASTER_IMPLEMENTATION_PROMPT.md` (especially the 'Prismatic Island Minimalism' / rainbow-edge concept). The original assignment, dataset, backend rules, trace requirements, approvals, evals, and financial invariants still control. Do **not** rebuild the system from scratch. Work incrementally in the existing app.

---

## 0. YOUR ROLE, QUALITY BAR & MANDATE

You are simultaneously a world-class digital creative director, award-caliber product designer, senior Next.js/React engineer, interaction designer, WebGL/Three.js artist, accessibility specialist, performance engineer, and AI application integrator.

Redesign **Mira**, the AI travel concierge for **Ceylon Compass Holidays**, into a polished, cinematic, modern luxury travel experience whose quality is immediately visible in actual browser screenshots.

A previous implementation has been judged too plain: bright white empty space, flat illustrated landscape art, generic small cards, conventional header and chat panel, weak visual hierarchy, little photographic storytelling, minimal depth, and no remarkable microinteractions. The attached `Mira-ChatGPT-Workflow-Report.pdf` depicts the previous version. Your job is to create a **dramatic yet tasteful upgrade** while retaining the product's reliability.

**Desired feel:** editorial travel magazine x luxury boutique hotel x futuristic AI concierge. An emotional first impression, exceptionally clear actions, elegant interaction, authentic Sri Lankan landscape photography, carefully layered depth, exceptional typography, a premium palette, one distinct but restrained WebGL moment, interactive itinerary storytelling, and exquisitely responsive layouts.

### Non-negotiables

1. **Do not make another generic SaaS dashboard.** No flat UI kit appearance, empty illustrative hero, stacked pills everywhere, giant gradient blobs, neon rainbow or full-screen AI chat with no imagery.
2. **Do not copy the reference sites pixel-for-pixel.** Borrow visual principles, composition, quality and motion, not logos, assets, prose or identical layout.
3. **Real, legally usable photography is essential.** Find, verify and incorporate compelling real photos of Sri Lanka. A travel app without rich imagery misses the brief.
4. **No rainbow gradient.** Use a deep-forest/ivory/warm-sun palette with precise orange, champagne and occasional teal highlights. Premium gradient effects, not multi-hue neon.
5. **Preserve business rules:** never generate prices through LLMs; never expose staff costs/margins; never render non-published tour content; never bypass approvals; no hallucinated policies, testimonials, awards, ratings, availability, itinerary details, or prices.
6. **Preserve agent functionality:** live LangGraph workflow, AG-UI/CopilotKit, catalog-validated generative components, pricing function, source links, traces, enquiries, staff and evaluation suite. Do not replace agent outputs with hard-coded fake examples.
7. **Real working software only.** No mock front-end pretending to connect, no inert buttons, no screenshot-only solution. Correct existing defects where encountered and report all changes.
8. **Brand-pack fidelity:** original brand pack is a contractual source of truth. Keep logo identity, orange `#F26B1D`, teal `#14837B`, white surfaces and Inter for functional UI. Extensions (forest, warm ivory, champagne, optional editorial display type) are subordinate to existing brand tokens; document any extension. `brand_pack.json` explicitly limits animation/transitions to <200 ms, forbids scroll-triggered/parallax animation, requests small white cards with only one accent per card. Honor these rules, especially in functional UI. No permanent glowing motion or auto-rotating scenes.
9. **Demo-safe:** aim for a striking first paint, but a low-power MacBook/mobile browser must remain usable. Hero 3D is progressive enhancement with a polished photo fallback, not a dependency for conversation or pricing.

---

## 1. INSPECT FIRST — DO NOT BLINDLY REPLACE FILES

Perform these concrete tasks before editing:

- Read the existing README, project structure, package manifests, Next.js/React pages, design tokens, Tailwind config, agent/AG-UI frontend integration, generated UI catalog, API client, auth/staff routes, and tests.
- Read `brand_pack.json`, original assignment brief, source content and current evaluation report if present. Identify assets already licensed and brand-approved.
- Run the documented startup command. Identify what actually works, and what is only reported to work. Do not assume local credentials, Langfuse or LLM APIs are configured.
- Open the site and capture baseline real screenshots at **1440x900, 1280x800, 768x1024, 390x844**. Capture homepage, chat/planner, verified quote, custom no-price handoff, and staff dashboard. Record existing defects and baseline build/test output.
- Read any supplied reference images. Interpret them as inspiration only:
  - `design/references/01-bridgeai-cinematic-hero.png`: dramatic immersive landscape hero, oversized typography, foreground/background layering, slim capsule navigation.
  - `design/references/02-editorial-nature-typography.png`: quiet editorial hierarchy, luminous sky/forest photography, typography balanced against landscape.
  - `design/references/03-immersive-travel-carousel.png`: destination-focused atmospheric background, elegant horizontally overlapping photo cards with depth and navigation.
  - `design/references/04-triplo-photographic-travel.png`: immersive large hero title, luxurious travel photography, strong photo-backed content followed by crisp white editorial sections.
- Create `docs/UI_BASELINE.md` with current-state screenshots and a short list of issues. Preserve existing functionality before major changes. Work in reviewable commits.

If reference files are not in the repo, use the textual descriptions above and proceed; do not block on a missing screenshot.

---

## 2. DESIGN CONCEPT — 'THE LIVING ISLAND'

### 2.1 Emotional positioning

The user is not browsing a booking spreadsheet. They are imagining a real trip. The interface should first make Sri Lanka *feel* worth visiting, then seamlessly convert excitement into a trustworthy, clearly priced, source-grounded journey.

**Core proposition:** "Your island. Your story." The hero should feel alive: mist, warm sunlight, forests, water, genuine landscapes, quiet depth and grounded human-scale typography. Mira acts as a sophisticated travel companion, not a corporate chatbot.

**Visual language:** cinematic, atmospheric, contemporary, calm, confident, tactile, handcrafted, refined, editorial, warm; 3D with purpose, not a tech demo.

**Avoid:** confetti backgrounds, purple AI gradients, random glassmorphism, busy bevels, neon outlines, tiny destination photography, huge blank white hero, full-page card grids with repeated appearances, generic Lucide icon-only filler, fake metric counters, intrusive popups, unnecessary motion.

### 2.2 Color system

Mandatory core from provided brand pack:
- Brand orange: `#F26B1D` (primary branded call-to-action, active selection, Mira mark)
- Base ink: `#111111` (main type)
- White: `#FFFFFF` (functional cards)
- Teal: `#14837B` (verified/status accent only)
- Other original accents are available but do not introduce a rainbow presentation.

Editorial extensions (do not overwrite source tokens):
- Ivory: `#FAF9F6` (light section backgrounds)
- Forest: `#17392F` (hero/nav/large atmospheric headings)
- Midnight green: `#102A25` (photographic overlays)
- Champagne: `#C5A778` (subtle highlight, thin decorative edge only)
- Mist: `#E9ECE7` (neutral separators)
- Quiet beige: `#F3EEE6` (warm backgrounds)

Set semantic design tokens (`--brand-primary`, `--text-strong`, `--surface-primary`, `--surface-warm`, `--accent-verified`, `--stroke-muted`, `--hero-overlay`) rather than sprinkling hex values through JSX.

**Premium gradients, not rainbow:**
- On dark photographic hero, apply black/forest gradients with transparent fade so images are legible, and warm golden light near the horizon.
- On light sections, extremely subtle ivory-to-white and pale champagne highlights only.
- For selected buttons use a short-lived moving **orange → champagne → soft teal light-trace** around a dark inner fill. This is a narrow stroke effect only, not a multicolor gradient-filled button.
- Buttons, cards and price panels must not violate one-accent-per-card rule.

### 2.3 Typography system

- Functional interface: **Inter** (from supplied brand pack), careful weights, non-shouting text, comfortable body sizes.
- Hero editorial type: bold expressive display scale with confident tracking and controlled line breaks; optionally introduce a single beautiful licensed editorial serif for a *decorative* hero phrase ONLY if this is truly better and documented as a brand extension; don't replace functional Inter.
- Desktop homepage title 80–132px depending on screen, fluid `clamp()` with carefully kerned lines; mobile 43–68px. Keep words readable rather than covering the subject.
- Body type comfortably 15–18px, neutral dark text. Pricing tabular numerals. Deliberate vertical rhythm. No excessive uppercase microtext.
- Suggested landing copy: **"Sri Lanka, beyond the ordinary."** / **"Your island. Your story."** Choose one with strong image composition, and keep narrative claims grounded.
- Useful smaller copy: "A personal way to explore the island. Tell Mira what moves you." Never say instant booking if booking is only mocked.

### 2.4 Layout and negative space

- Homepage: cinematic photograph as the dominant visual, not a full white page with a central illustration. Use approximately full-viewport composition at desktop with a clean overlay for readability and visible message entry.
- Max content width around 1440px, editorial gutters (desktop ~5–7vw, mobile 20–24px), flexible CSS grid.
- Use overlapping/tucked layers sparingly: floating navigation with depth, one photo deck, a calm prompt composer, a concise trust strip below the fold.
- Use geometry to make layout memorable: gracefully rounded/arched media masks where justified, layered photo edges, a slim vertical index, asymmetrical but balanced sections.
- Avoid fake navigation links: all meaningful links must lead to implemented routes/actions or be removed.

---

## 3. IMAGE ACQUISITION: SOURCE, LICENSE, IMPLEMENT

Photography is a required design deliverable, not a placeholder for later.

### 3.1 Concrete image leads, confirmed as individual free-photo pages

Start with these **Unsplash source pages** (not hotlinks to screenshots of other travel websites). Verify each image's free license on its page before downloading, avoid sponsored/Unsplash+ results, and keep attribution/source metadata in a manifest.

1. **Sigiriya / Rock fortress:** https://unsplash.com/s/photos/sigiriya-sri-lanka — search this collection and select a genuine strong aerial or sunrise image marked free under Unsplash License. (An especially promising photographer lead for Sigiriya is https://unsplash.com/@lahiru_iddamalgoda; inspect the photo license and composition.)
2. **Ella / Nine Arches Bridge with train:** https://unsplash.com/photos/a-train-traveling-over-a-bridge-over-a-lush-green-forest-wN6bY2hovUE
3. **Ella / alternate train image:** https://unsplash.com/photos/a-train-traveling-over-a-bridge-in-the-middle-of-a-forest-gE1qG4s8DKY
4. **Mirissa / palm beach:** https://unsplash.com/photos/a-beach-with-palm-trees-and-a-body-of-water-XffcuIspsVA
5. **Mirissa / aerial coast:** https://unsplash.com/photos/an-aerial-view-of-a-beach-with-palm-trees-4CPF_TglMDc
6. **Galle Fort coastline:** https://unsplash.com/photos/a-scenic-view-of-a-landscape-with-buildings-Kwg9nw76Ku4
7. **Tea country:** https://unsplash.com/s/photos/tea-sri-lanka — choose an individually verified free photo, not a paid search result.

Other legally usable sources: https://www.pexels.com/ and https://unsplash.com/. License summaries: https://unsplash.com/license and https://www.pexels.com/legal-pages/license/ . No attribution is generally required for licensed free media, but maintain credits to be professional; verify on each asset. Do not assume search engine images are licensed. Never use Getty, watermark previews, other travel companies' site photos, or screenshot references as deployed production media.

### 3.2 Required asset work

- Select at least **one cinematic hero photo** (Sigiriya or Nine Arches) + **five varied Sri Lanka travel photos** (Ella, coast, heritage, hills, wildlife only if actually relevant/available).
- Acquire and store **licensed image files** under `public/media/destinations/` if network/tool access allows. Prefer local build assets rather than runtime reliance on third-party hotlinks. If downloading fails, use existing licensed local assets, and explicitly document blocked external acquisition; do not leave broken images.
- Generate optimized responsive variants where feasible: hero wide 2000–2400px, medium 1280px, small mobile crop 768px; card variants 800–1200px. Use WebP/AVIF when supported. Maintain full-quality originals outside production asset output if needed.
- Use Next.js `<Image>` with `sizes`, `priority` for LCP hero where suitable, blur placeholders (real local images), image-safe overflow and proper focal positioning. Ensure faces/landmarks stay visible across crops. No stretched images.
- Create `src/data/media-manifest.ts` and `docs/ASSET_LICENSES.md` recording for EACH image: local asset filename, landmark/location, source page URL, author, verified license, and date checked.
- Link assets to known, published tour/destination IDs from dataset; never infer that the photographed hotel or itinerary stops are included in a tour. Mark photos as editorial imagery where needed. No fake testimonials or 5-star reviews.
- Original user-provided design reference screenshots belong ONLY in `design/references` (local design input). **Do not ship them in the website bundle.**

---

## 4. HOMEPAGE — MAKE THE FIRST THREE SECONDS UNFORGETTABLE

### Desktop visual target

**A. Hero: 85–100svh immersive photo.** Crisp aerial Sigiriya / misty Ella / lush forest edge-to-edge, layered with tasteful cinematic dark/forest gradient for contrast. Great lighting and intentional composition. The background photo should carry most of the emotional impact; 3D complements rather than obscures it.

**B. Navigation: floating premium capsule.** A compact translucent-ivory/soft-blurred or dark-tinted floating nav near top, restrained shadows and hairline stroke; brandmark on left, meaningful links (Explore, Journeys, How Mira Works), "Plan my trip" primary CTA, accessible staff link in non-prominent account menu if appropriate. On mobile: brandmark + accessible menu icon + clear CTA. Don't replicate screenshot brands.

**C. Large editorial headline.** Strong, readable, not centered by default. Two or three short lines. Use a deliberate asymmetric composition, perhaps left-aligned over darker portion of photography and a small photo caption/scene location in the opposite corner.

**D. Conversational entry is visible immediately.** Beautiful floating prompt composer inside/below hero: multi-line freeform input, one expressive orange send button, 2–3 meaningful prompt chips; realistic text "Ask Mira to plan your Sri Lankan journey...". The user can type and submit directly; on submit navigate or transition to planner while preserving entered text and initiating the actual agent. This must not be a dead placeholder.

**E. One purposeful accent.** A micro-label ("CEYLON COMPASS HOLIDAYS / MEET MIRA") and a subtle scenic location caption. Photographic trust, not fake review numbers.

**F. Mobile first-class version.** Mobile hero photo with correct focal crop, 44px+ tap controls, title sufficiently high, bottom-safe composer, navigation that does not cover imagery. No horizontal scroll.

### Below the fold

1. **Signature journeys editorial gallery:** Three or four genuinely published tours / destination cards in a staggered grid or curated photo deck, respecting source and status; minimum one large anchor card and smaller contrasting ones. On hover cards use subtle 2.5D depth/lighting rather than giant movement; on touch show real tap controls. Clicking cards opens destination/tour pages or calls the tour selection flow.
2. **'Meet Mira' / 'From conversation to journey' section:** short actual 3-step explainer (discover preferences → explore published tours → verified quote or specialist handoff) with well-designed imagery, not icon spam.
3. **Featured story:** split photograph + editorial copy for one real supported destination, with actual content excerpts/citations.
4. **Live Mira demonstration:** mini non-fake UI excerpt demonstrating what a source-backed itinerary/quote looks like, if possible sourced from actual data. Do not use arbitrary illustrative USD prices; an example must be explicitly tied to a date/group and verified.
5. **Strong closing CTA:** large quiet full-width image band with prompt input or "Start planning with Mira" action.
6. **Footer:** brand, functional navigation, mock booking disclosure if relevant, privacy/contact only if real/implemented.

### Photo-first destination deck inspired by reference image 03

Build an interactive gallery with:
- Large scenic background image that changes according to highlighted **published** tour.
- 3–4 overlapping / staggered portrait destination cards (e.g. Sigiriya, Ella, Mirissa, Kandy subject to dataset).
- A visually strong number/index and calm navigation arrows (keyboard and button accessible).
- Fade/crossfade and subtle 3D card transform without a heavy carousel dependency unless justified.
- Card has a source-supported destination label, duration if sourced, a clear actionable CTA, image, and at most one accent color. Never show teaser price unless it is calculated for explicit valid party/date and verified by the deterministic pricing service.
- Accessible alternative list for reduced-motion and mobile.

---

## 5. PREMIER ANIMATED BUTTON — LIGHT-TRACE BORDER RUNNER

Implement a reusable `PremiumActionButton` with variants `primary`, `light`, `quiet`, `outline`, `dark`. The signature version should visually feel crafted:

- Inner fill **deep forest** or brand orange, legible white text, pill shape per brand pack.
- A 1–2px **animated conic-gradient stroke** appears on **hover or keyboard focus**. It visually sweeps from warm orange through champagne into a very slight teal glint; no purple, no all-color rainbow.
- Use a wrapper/pseudo-element with mask so the gradient is visible **only on the border**, not over the label. Pure CSS `conic-gradient`, optional registered `@property --angle`, support safe fallback in browsers without animated custom properties. Trigger once on interaction, **finish under 200ms** to respect brand motion guidance; avoid perpetual spinning.
- Add a tiny accessible arrow icon whose position/shape transition completes within 150–180ms. Provide `:focus-visible` outline separate from the decorative runner; focus must still be obvious with motion disabled.
- Pointer magnetic attraction should be **very subtle or skipped** if it impairs targeting. No fake physics cursor or cursor replacement.
- Maintain contrast >=4.5:1 normal text, no label movement that makes clicks harder, no hover-only affordances on touch.
- Animate via GPU-friendly transform/opacity. Do not animate layout-affecting properties or trigger huge box shadows every frame.
- Unit/component test that effect does not swallow pointer events, and button clicks are real.

Also create restrained `PhotoCard` hover treatment: soft 3D tilt 2–4 degrees max, image zoom <=1.04, directional highlight, border glow opacity subtle, transform completes under 200ms. Disable tilt for reduced motion/touch. Nothing should jiggle continuously.

---

## 6. 3D/WebGL — ONE SIGNATURE MOMENT, NOT A GIMMICK

Use **Three.js with React Three Fiber (`@react-three/fiber`) and Drei (`@react-three/drei`)** for **one meaningful, isolated interactive scene** only if tests show it performs well. Do **not** add a huge scene to every page.

**Recommended scene: 'Living Island / Journey Atlas'**

An elegant small interactive 3D object layered in a portion of the homepage hero or "Explore Sri Lanka" section: a textured semi-stylized relief/map-inspired sculpture of Sri Lanka or an original 3D compass/sphere with 3–4 source-backed geographic waypoints. Interaction:
- Pointer tilt reacts gently (3–5°) on desktop, no excessive movement; no fake geospatial location pins.
- Hover/tap highlights a real tour/destination and updates the adjacent 2D destination card or photo. Must work equally on mouse and touch via accessible list/card controls.
- Atmospheric forest/bronze lighting, subtle ambient occlusion if affordable, no oversaturated neon, no 3D text that obstructs the booking UI.
- If a suitable licensed 3D island geometry cannot be sourced quickly, create an original procedural **floating compass and layered photo planes** rather than downloading an unlicensed model. Never pretend a random 3D rock is Sigiriya.
- **No perpetual rotation or scroll-triggered parallax.** Use pointer-driven movement with a quick response and reduced-motion fallback. Keep static state beautiful.
- Lazy-load with `next/dynamic(..., {ssr:false})` or equivalent client-only boundary; only mount when in/near view and capable, remove when hidden, `frameloop="demand"` where possible. Use low DPR, light geometry, tiny textures, no oversized post-processing shaders.
- Respect `prefers-reduced-motion`, touch, small screens, WebGL failure, battery/performance constraints. Always render a **real photograph fallback** that looks intentional. 3D must never cover form input or prevent navigation.
- Document scene purpose, performance impact, and why it improves discovery rather than just adding spectacle.

Consider **CSS perspective + Motion for React** for 2.5D photo stacks and cards; use WebGL only where it adds unique value. Prefer official stable package releases verified against existing React/Next versions; don't install bleeding-edge alpha versions.

Important: `brand_pack.json` forbids **scroll-triggered and parallax animations** and restricts transitions to <200ms. Do not add GSAP ScrollTrigger, Lenis smooth-scroll, locomotive-scroll, endless hero animations or scroll-jacking. The requested premium experience should feel refined with interaction-based depth and carefully composed static imagery, not rely on cinematic scroll tricks that violate the source rules.

---

## 7. MIRA PLANNER — THE MAIN PRODUCT EXPERIENCE, NOT JUST CHAT

The strongest part after landing must be the actual generative journey experience.

### Desktop composition

- Premium content header and a compact location breadcrumb, separated from the immersive home hero; don't overload traveller workspace with flashy effects.
- Two-column layout: ~40% conversational interaction + ~60% **living journey canvas**. Both surfaces harmonize on warm white/ivory backgrounds. Sticky, sensible but avoid scroll traps.
- Chat bubbles are calm and typographic. Distinguish Mira, traveler, sources, and tool status without colored blocks everywhere.
- On the right, agent-selected **real validated UI components**: `TravellerPicker`, `TourCard`, `ItineraryDay`, `PriceBreakdown`, `BookingForm`, `EnquiryNotice`, plus optional `DestinationHero`, `JourneyTimeline`, `SourceCitation`, `TourComparison`, `BookingStatus` (all registered/strictly validated).
- Tour cards now use authentic licensed photos, confident titles, clear type labels, source citations and direct selection. No generic flat thumbnails.
- Itinerary panel displays a scenic photo strip (from published sources) above a real day-by-day route/list. No invented stops/timing.
- Pricing card is exceptionally clear: VERIFIED BY WORKBOOK badge, full traveler-visible amount, exact deposit, dates and party size, and source link. **No cost or margin fields in network responses.** If rate missing/expired, hide price amounts entirely and show thoughtful specialist handoff with actual saved enquiry ID.
- Agent-driven UI must update as state changes: preferences -> published tour suggestions -> source-backed itinerary -> verified quote -> booking/enquiry. Make changes visually smooth but never fabricate UI data.
- Streaming indicators must be honest (thinking, retrieving, checking rates) and not misrepresent executed tools. Errors show safe recovery, never blank screen.
- Chat input and action controls stay responsive. The scenic 3D effects are **not** in the critical planner or quote flow.

### Mobile composition

- One column, with segmented tabs **Conversation / Your journey** (similar to existing flow but styled at premium quality) and a persistent accessible prompt composer.
- Don't make desktop split UI simply squash; each panel must be deliberately reflowed.
- Journey cards, source citations, prices and booking forms must fit 360–390px screens without horizontal overflow.
- Have meaningful skeletons, empty states, expired rates, unsupported custom trips, booking mocked decline/retry and offline/LLM error states.
- Returning visitor greeting can show prior verified quote only when actual visitor history has been persisted and consent/access conditions respected.

---

## 8. STAFF CONSOLE DESIGN

Restyle the private staff experience as restrained premium enterprise software, distinct from cinematic traveler marketing. White panels, clear data tables, high contrast, muted badges, truthful statuses, readable cost vs selling price vs gross profit, filtered enquiries, staff notes, protected Approver workflow and clear publishing state.

No photo hero or 3D canvas in staff views. Never compromise information density or financial clarity. Preserve role-based access on the server, not only frontend checks. Staff metrics must come from real database records, not fake KPI tiles.

---

## 9. FRONTEND ENGINEERING & LIBRARY CHOICES

Reuse the current framework where practical; do not replace stable backend plumbing to chase style. If project already uses Next.js App Router + Tailwind + CopilotKit/AG-UI, keep it.

Recommended **specific responsibility** for each library:

- **Next.js / React / TypeScript:** app structure and typed feature boundaries.
- **Tailwind CSS + project CSS variables:** responsive components, style tokens, premium gradients, mask effects.
- **Motion for React (`motion/react`):** small, accessible interaction transitions, hover/tap, panel entry; `MotionConfig reducedMotion="user"` / `useReducedMotion`. Match <200ms rule.
- **Three.js + React Three Fiber + Drei:** one lazy-loaded enhanced scene, subject to performance validation.
- **Next.js `Image`:** responsive image optimization, sizes, priority and blur; no huge images in core LCP.
- **Lucide only where needed:** UI micro-icons, no icon graveyard.
- **Existing AG-UI/CopilotKit runtime:** do not replace with hand-coded chat that only *looks* dynamic.
- **Existing Zod/Pydantic schemas:** strict validation on both sides, especially UI component props and pricing response DTO.

Avoid installing unnecessary animation frameworks. Prefer CSS/Motion first. Do not add GSAP unless you can identify a compliant and otherwise impossible interaction; do not build scroll-driven animations. Avoid glTF models from random marketplaces without rights.

### Components you should implement

`CinematicHero`, `FloatingNav`, `BrandMark`, `HeroPromptComposer`, `PremiumActionButton`, `DestinationPhotoDeck`, `DestinationFeatureCard`, `SourceBackedTourCard`, `JourneyCanvas`, `TimelineDay`, `TrustedPriceBreakdown`, `SpecialistHandoffPanel`, `AgentResponseSkeleton`, `MobilePlannerTabs`, `AmbientDepthScene` (optional WebGL enhancement), `MediaCreditLink` (optional), `StaffDataTable`.

Build components as reusable, typed and semantic. Use ARIA labels where meaningful, not random `div onClick` in place of buttons. The hero composer must dispatch an actual agent turn through existing integrations.

---

## 10. 3D/MOTION SAFETY, ACCESSIBILITY AND PERFORMANCE

**Hard quality gates:**

- All core tasks (prompt, tour selection, quote, enquiry, mock booking) work with JavaScript-enabled React **even if the WebGL scene fails**.
- Real semantic controls, keyboard-accessible nav/menu, visible focus rings, source URLs reachable, live region for important agent changes without excessive announcements, readable image overlays, accessible sliders/carousel buttons.
- `prefers-reduced-motion` removes decorative movement/3D tilt, with static premium imagery remaining.
- Hero's first paint must not wait for model network/API. No enormous 3D bundle on the initial critical path.
- No sticky trapping, no surprise scroll-to-bottom, no layout shifts from image loads, no accidental scrollbar, no long-running 3D frame loop on hidden tabs.
- Optimize layout for 390px, 768px, 1280px, 1440px and 1920px; also test 320px narrow width. Touch target 44px+ where feasible.
- Aim for desktop Lighthouse >=90 for performance and accessibility, mobile performance >=80 if environment permits. These are goals, not reported scores until measured. Fix Core Web Vitals regressions; target LCP <2.5s on realistic production-like connection where feasible, CLS <0.1. Record actual results and environment.
- All hero and tour photos have accurate alt text; decorative textures are `alt=""`. Never use photo backgrounds without adequate text contrast overlay.
- E2E screenshots must be from the **real app**, not generated mockups or user-provided reference screenshots.

---

## 11. PRESERVE EXACT FUNCTIONAL & DATA INVARIANTS

The attached original assignment contains requirements 1–8 and bonuses. Do not break them for design. Add tests for these flows **after the visual refactor**, not just unit tests for new components:

1. A quick-booker can ask for a Sigiriya day trip, provide valid party/date, see a published itinerary and a **code-calculated** quote if valid. Use source workbook rules and exact relevant sample dates; no universal teaser amount. When the example fixture is 2 adults, 10 Jan 2027, the supplied sample Q-1041 is USD 315 with USD 315 deposit — only display when the current pricing engine independently agrees.
2. A 10-day custom Kandy–Ella family trip with no complete rates must **never** display invented price; should show relevant published alternatives and save a private specialist enquiry.
3. A returning traveler should see their own stored last quote (if implemented), not another visitor's data.
4. Draft/unapproved tour text must not appear in traveler retrieval or public card grids.
5. Staff can review enquiries/finance and only Approver may publish generated content; verify authorization on API.
6. Mock booking/payment failure displays human-friendly recovery + retry with genuine application behavior.
7. Every generated UI payload passes the strict component catalog validator before browser rendering.
8. Each traveler turn is traceable to model calls, content retrieval, price tool and UI render decisions; private identifiers excluded from traces.
9. Keep existing evaluations; aim for 40+ total with multi-turn, prompt injection, price correctness, no-price and UI validity checks. Do not claim unsupported success.
10. Keep configurable `TODAY_DATE` / eval date 2026-11-19 for deterministic rates.

**Known existing report context:** The user-provided `Mira-ChatGPT-Workflow-Report.pdf` reports locally observed numbers 48/49 conversation evals, 20/21 exact quote/deposit, 10/10 no-price, 58/58 UI validation, plus a disagreement in Q-1043: sample email says USD 2680, workbook-based result reportedly USD 2965 / deposit USD 742. Treat this as a **reported existing result**, not proof of current runtime correctness; re-run before claiming anything. Do not "fix" Q-1043 by overriding workbook pricing to match a conflicting sample email.

---

## 12. IMPLEMENTATION ORDER — ACTUAL CODE CHANGES, NOT A PLAN-ONLY RESPONSE

Create focused, reviewable commits where possible. Do not perform a risky big-bang rewrite.

**Phase A — audit and photographic asset pass:** run baseline/screenshots/tests; identify current design tokens, acquire licensed photography, create manifest and consistent image crop presets.

**Phase B — breathtaking real landing page:** ship scenic hero, typography, nav, functional prompt composer, mobile crop, scenic editorial sections, real published tour cards.

**Phase C — signature interactions:** implement gradient light-trace border button, refined 2.5D cards/gallery and transitions with reduced-motion handling. Verify screenshot/interaction quality.

**Phase D — optional signature WebGL scene:** implement React Three Fiber progressive enhancement; only keep if it materially improves quality and passes performance and fallback tests. Prefer an attractive, functioning, photo-only result to a broken 3D experiment.

**Phase E — premium journey canvas:** restyle live AG-UI components, genuine tour photo cards, itinerary, sourced content, verified price, specialist handoff, responsive mobile planner, staff console.

**Phase F — regression and polish:** pricing/unit tests, E2E browser flows, 40+ eval suite if available, mobile/desktop real screenshots, inspect layout problems and correct them.

At each phase:
- State modified files; exact commands run; tests/screenshots observed; known failures; what will be tackled next.
- If a dependency is unavailable, gracefully skip and document rather than claim it worked.
- Keep an archive or before/after screenshot set in `docs/screenshots/before/` and `docs/screenshots/after/`. Do not deploy reference design images.
- Do not spend the entire time on decorative 3D; functionality and score-critical price correctness take priority.

---

## 13. ACCEPTANCE CHECKLIST — MUST PROVE THE REDESIGN

### Visual

- [ ] Homepage visibly resembles a high-end Sri Lankan travel editorial product rather than a prototype.
- [ ] Real high-resolution, correctly licensed Sri Lankan landscape photography actually renders, with accurate cropping and no broken image links.
- [ ] Hero is cinematic and expressive, not the previous flat SVG illustration.
- [ ] Floating nav and premium large typography are deliberate, balanced and legible.
- [ ] Color treatment is forest/ivory/orange/champagne, no rainbow gradients or neon.
- [ ] Hover/focus gradient border runner is visibly implemented, accessible and <200ms.
- [ ] Destination gallery has crafted 2.5D depth and actually responds to user interaction.
- [ ] At least one actual WebGL/React Three Fiber scene is implemented if the environment can support it without significant regressions; otherwise document a genuine attempted spike and keep the excellent CSS/photo fallback.
- [ ] 390px phone and 1440px desktop both look intentionally designed.
- [ ] Page isn't a pasted reference template; Mira/Ceylon Compass has its own visual identity.

### Product

- [ ] Typing on the homepage starts a real Mira agent turn and produces validated UI.
- [ ] Quick tour can show correct priced quote and deposit with source.
- [ ] Unsupported custom journey gracefully hands over without any price.
- [ ] Tour content is published-only and image mapping never invents tours.
- [ ] Staff dashboard retains protected finance and approvals.
- [ ] Traces and evaluations still work to the degree supported by available credentials/setup.
- [ ] Mock payment/booking failures have real, clear recovery.

### Engineering

- [ ] TypeScript and Python type/build checks pass (as applicable).
- [ ] Test and e2e scripts execute; show actual pass/fail counts.
- [ ] Reduced motion and failed WebGL fallback verified.
- [ ] No major accessibility violations on critical pages; measurable performance and mobile results reported.
- [ ] `docs/ASSET_LICENSES.md` exists with actual photo sources and authors.
- [ ] Real screenshots collected for homepage, planner, quote, no-rate, mobile and staff views.
- [ ] `docs/UI_REDESIGN_REPORT.md` includes architectural decisions, tradeoffs, before/after screenshots, measured results, remaining limitations.

---

## 14. FINAL REQUIRED OUTPUT FROM CODEX

Do the implementation. At the end, provide:

1. A short visual/design summary explaining choices and comparison against supplied references.
2. List of actually implemented files and components, grouped by phase.
3. URLs for the running app pages (only if running and verified).
4. Precise commands actually run and their results; no imaginary test report or fake green statuses.
5. Paths to real screenshot files; show a real desktop and mobile screenshot in the working environment where possible.
6. Actual asset license manifest and all image sources.
7. Whether WebGL/3D ran, how it falls back and any performance costs.
8. Whether the hero button border runner works with mouse, keyboard, touch and reduced motion.
9. Regression status of pricing, AG-UI, tracing, enquiries and staff approvals.
10. Remaining blockers and the three highest-impact next improvements.

**START NOW:** Inspect the repository and existing files, run the app, establish the current behavior, then IMPLEMENT the new photographic hero and premium design system. Do not ask for another design brief or stop at moodboards. Maintain clean, understandable engineering suitable for a technical live demo.

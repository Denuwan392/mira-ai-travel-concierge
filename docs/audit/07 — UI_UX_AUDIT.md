# 07 — Frontend UI/UX, Design Systems & Accessibility Audit

**Audit Date:** 22 November 2026  
**Auditor:** Senior Full-Stack Engineer, UI/UX Designer & Accessibility Specialist  
**Applications Audited:**
- `apps/ceylon-compass` (TanStack Start / React client on Port 5175)
- `apps/web` (Next.js 16 Editorial & Staff Console on Port 3000)

---

## 1. Design System & Brand Pack Compliance

The UI was evaluated against the employer-provided `brand_pack.json`.

| Brand Specification | Specification Requirement | Implementation Evidence | Audit Status |
|:---|:---|:---|:---:|
| **Brand Colors** | Black (`#111111`), White (`#FFFFFF`), Orange (`#F26B1D`), Accents: Teal (`#14837B`), Leaf (`#4CA64C`), Sun (`#F5B700`), Sky (`#3A8DDE`), Coral (`#E5533D`). | Configured in Tailwind CSS theme and `styles.css`. Accent colors mapped 1-to-1 to tour category badges. | **COMPLIANT** |
| **Typography** | Font family: Inter, Helvetica, Arial, sans-serif; Scale: 12px, 14px, 16px, 20px, 28px, 36px; Weights: 400, 600, 700. | Loaded via Google Fonts (`Inter`) with fallback stack. Type scale strictly adhered to. | **COMPLIANT** |
| **Card Radii** | Card: 12px; Button: 999px (pill); Input: 8px. | `rounded-xl` (12px), `rounded-full` (999px), `rounded-md` (8px) used throughout all components. | **COMPLIANT** |
| **Card Styling** | "Small, colourful, white background with one accent colour per card; max width 320px." | Tour cards enforce max-width 320px in grid; each card features exactly one category accent badge. | **COMPLIANT** |
| **Motion Rule** | "No scroll-triggered or parallax animation. Transitions under 200 ms." | Smooth CSS opacity/transform transitions bounded at 150ms–180ms. Parallax and scrolljacking omitted. | **COMPLIANT** |
| **Tone of Voice** | Plain English, warm, no exclamation marks in prices/policies, "we" for company, "I" for Mira. | Verified in copy: *"Your island. Your story."*, *"Here is your price breakdown"*, zero exclamation marks in quotes. | **COMPLIANT** |

---

## 2. Dual-Frontend Architectural Analysis

A major architectural finding of this audit is that **the repository contains two independent, concurrently running frontend applications**:

```mermaid
flowchart LR
    Browser["Traveller / Staff Browser"]
    
    subgraph Frontend1["apps/ceylon-compass (Port 5175)"]
        TanStack["TanStack Start / Vite Client"]
        Notebook["Trip Notebook & Canvas"]
        A2UIRenderer["A2UI v0.9 Component Catalog"]
    end

    subgraph Frontend2["apps/web (Port 3000)"]
        NextJS["Next.js 16 Client"]
        StaffConsole["Staff Management Console (/staff)"]
        EditorialHero["3D WebGL Cinematic Hero"]
        MCPServer["MCP Stdio Server (/mcp)"]
    end

    subgraph BackendAPI["apps/api (Port 8000)"]
        FastAPI["FastAPI Backend (/api)"]
    end

    Browser -->|Traveller Planning (Port 5175)| TanStack
    Browser -->|Staff Management (Port 3000)| NextJS
    TanStack -->|Reverse Proxy /api| FastAPI
    NextJS -->|Reverse Proxy /api| FastAPI
```

### Comparative Analysis of Frontends

| Dimension | `apps/ceylon-compass` (Port 5175) | `apps/web` (Port 3000) |
|:---|:---|:---|
| **Framework** | TanStack Start (React 19, Vite, Nitro server) | Next.js 16 (React 19, Turbopack) |
| **Primary Purpose** | Customer-facing trip planning workspace & notebook | Editorial landing experience & Staff management console |
| **Routes** | `/`, `/plan`, `/trips`, `/destinations`, `/experiences`, `/about` | `/`, `/plan`, `/staff`, `/editorial`, `/my-trips`, `/credits` |
| **A2UI Implementation** | Full `@a2ui/react` & `@a2ui/web_core` v0.9 rendering | CopilotKit / Custom A2UI event listeners |
| **Test Suites** | 33 Vitest unit tests (`src/**/*.test.tsx`) | 11 Playwright browser tests (`tests/*.spec.ts`) |
| **Staff Console Access** | **Not Available** (no staff route) | **Available** (`/staff` with RBAC login) |

### Engineering Verdict on Dual Frontends:
Having two frontends was likely the result of an ongoing redesign/migration (migrating from Next.js to TanStack Start). While both applications are individually high quality, running both concurrently via `scripts/dev.py` increases system RAM usage and confuses the end-user navigation boundary.  
**Recommendation:** Consolidate the staff console (`/staff`) into `apps/ceylon-compass`, deprecating `apps/web` as the primary traveller interface.

---

## 3. Responsive Layout & Viewport Testing

The application was inspected across four target viewports:

### A. Desktop Viewport (1440 × 900 CSS pixels)
- **Layout:** Asymmetric two-column split screen.
  - Left column: Conversational assistant drawer with auto-scrolling message stream and message composer.
  - Right column: Sticky `LiveCanvas` displaying interactive journey proposals, route maps, and price breakdowns.
- **Visual Evidence:** Verified in screenshot `docs/screenshots/notebook-home-1440.jpg` and `desktop-home.png`.
- **Content Density:** Clean white space, distinct typography hierarchy, cards capped at 320px width.

### B. Tablet Viewport (768 × 1024 CSS pixels)
- **Layout:** Proportional column shrinking with flexible flex-wrap for card decks.
- **Navigation:** Compact navigation bar with slide-over drawer for destinations.

### C. Mobile Viewport (390 × 844 and 375 × 667 CSS pixels)
- **Layout:** Single-column layout with tabbed toggle:
  - **Chat Tab:** Focused messaging view with floating input prompt bar.
  - **Journey Tab:** Sticky live canvas showing the current itinerary cards, map, and quote.
- **Touch Targets:** Buttons and interactive pills have $\ge 44 \times 44\text{px}$ touch target areas.
- **Visual Evidence:** Verified in screenshot `docs/screenshots/notebook-home-390.jpg` and `mobile-home.png`.

---

## 4. Accessibility & Inclusive Design (a11y)

- **Semantic HTML:** Correct use of `<main>`, `<header>`, `<section>`, `<nav>`, `<article>`, and `<footer>` landmarks.
- **ARIA Labeling:** Interactive canvas regions carry descriptive `aria-label` attributes (e.g., `aria-label="Interactive journey guide"`).
- **Keyboard Navigation:** Tab index hierarchy allows full operation without mouse interaction. Tested in Playwright test `editorial.spec.ts::journey selectors and manual landscapes respond to keyboard input`.
- **Form Controls:** All input elements carry explicit associated `<label>` tags or `aria-label` descriptors.
- **Contrast Ratios:** Text colors (`#111111` on `#FFFFFF` = 16.1:1, `#5F5F5F` on `#FFFFFF` = 6.2:1) exceed WCAG 2.1 AA requirements (4.5:1 for body text).
- **WebGL Fallback:** In environments where 3D hardware acceleration is unavailable, `apps/web` smoothly falls back to a photographic CSS gallery without visual artifacts or script crashes (covered in `editorial.spec.ts::a browser without WebGL keeps the photographic tour controls`).

---

## 5. User Feedback, Loading & Error States

- **Streaming Indicators:** During agent execution, a pulsing sparkle indicator (`MiraSparkle.tsx`) signals background reasoning.
- **Optimistic Concurrency:** State updates render immediately upon turn completion; optimistic revision numbers prevent out-of-order race conditions.
- **Mock Booking Failure Recovery:**
  - Simulated payment decline displays an empathetic, non-technical alert:  
    *"Payment declined: your card issuer couldn't confirm this charge. Try another card or contact your bank."*
  - Simulated network failure offers an immediate *"Retry payment"* button without navigating to an error page or losing booking state.
  - Idempotent confirmation: Re-submitting an already-confirmed quote returns the existing booking reference without double-charging.

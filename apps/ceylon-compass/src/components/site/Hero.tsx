import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { HERO_SLIDES } from "@/lib/content";
import { photos } from "@/lib/photos";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { cn } from "@/lib/utils";
import { MiraSparkle } from "./MiraSparkle";
import { PromptBar } from "./PromptBar";

const AUTOPLAY_MS = 7000;

const accentText = {
  saffron: "text-saffron",
  "saffron-wash": "text-saffron-wash",
  "maroon-wash": "text-maroon-wash",
} as const;
const accentBg = {
  saffron: "bg-saffron",
  "saffron-wash": "bg-saffron-wash",
  "maroon-wash": "bg-maroon-wash",
} as const;

export function Hero() {
  const [active, setActive] = useState(1);
  const [prev, setPrev] = useState<number | null>(null);
  const [paused, setPaused] = useState(false);

  const reduced = useReducedMotion();
  const controlsRef = useRef<Array<HTMLButtonElement | null>>([]);

  const go = useCallback(
    (i: number) => {
      if (i === active) return;
      setPrev(active);
      setActive(i);
    },
    [active],
  );

  useEffect(() => {
    if (prev === null) return;
    const t = window.setTimeout(() => setPrev(null), 800);
    return () => window.clearTimeout(t);
  }, [prev, active]);

  useEffect(() => {
    if (paused || reduced) return;
    const t = window.setTimeout(() => go((active + 1) % HERO_SLIDES.length), AUTOPLAY_MS);
    return () => window.clearTimeout(t);
  }, [active, paused, reduced, go]);

  const onKeys = (e: KeyboardEvent<HTMLDivElement>) => {
    const n = HERO_SLIDES.length;
    let next: number | null = null;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = (active + 1) % n;
    if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = (active - 1 + n) % n;
    if (e.key === "Home") next = 0;
    if (e.key === "End") next = n - 1;
    if (next !== null) {
      e.preventDefault();
      go(next);
      controlsRef.current[next]?.focus();
    }
  };

  const slide = HERO_SLIDES[active]!;
  return (
    <section
      data-nav-theme="hero"
      aria-roledescription="carousel"
      aria-label="Sri Lanka destinations"
      className="cinema-hero relative isolate flex min-h-[max(660px,85svh)] flex-col overflow-hidden bg-charcoal text-on-dark"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={() => setPaused(false)}
    >
      {/* Photography layers */}
      <div className="absolute inset-0 -z-20">
        {prev !== null && (
          <div className="absolute inset-0 overflow-hidden">
            <img
              src={photos[HERO_SLIDES[prev]!.photo].src}
              alt=""
              aria-hidden
              className="h-full w-full scale-[0.94] object-cover brightness-75 transition-[transform,filter] duration-700 ease-editorial"
              style={{ transformOrigin: "70% 50%" }}
            />
          </div>
        )}
        <div key={slide.id} className={cn("absolute inset-0 overflow-hidden", !reduced && "animate-mask-up")}>
          <img
            src={photos[slide.photo].src}
            alt={photos[slide.photo].alt}
            className="h-full w-full object-cover transition-transform duration-300 ease-out"
            style={{ objectPosition: "65% 50%" }}
            fetchPriority={active === 0 ? "high" : undefined}
          />
        </div>
      </div>
      <div className="absolute inset-0 -z-10 bg-hero-left" aria-hidden />
      <div className="absolute inset-0 -z-10 bg-hero-bottom" aria-hidden />
      <div className="absolute inset-x-0 top-0 -z-10 h-40 bg-gradient-to-b from-ink/55 to-transparent" aria-hidden />

      {/* Destination name behind the type */}
      <div aria-hidden className="pointer-events-none absolute inset-x-0 bottom-[10%] -z-10 overflow-hidden px-5 md:px-10">
        <span key={slide.id} className={cn("block text-[24vw] leading-[0.8] font-semibold tracking-[-0.07em] text-outline-light whitespace-nowrap md:text-[19vw]", !reduced && "animate-ghost")}>
          {slide.name}
        </span>
      </div>

      <div className="mx-auto flex w-full max-w-[1440px] flex-1 flex-col px-5 pt-[104px] pb-6 md:px-10 md:pt-[120px]">
        <div className="max-w-[760px]">
          <p className="eyebrow flex items-center gap-2 text-on-dark/85">
            <MiraSparkle className="size-3.5" /> AI-crafted journeys · Sri Lanka
          </p>
          <h1 className="display-xxl mt-5 text-on-dark">
            Sri Lanka,
            <br />
            <span className="serif-italic font-normal tracking-[-0.03em]">without limits.</span>
          </h1>
          <p className="mt-6 max-w-[440px] text-[15px] leading-relaxed text-on-dark/80 md:text-base">
            Describe the trip you're imagining. Mira sketches a route in seconds, and a specialist makes every detail real.
          </p>
          <div className="mt-7 flex flex-wrap items-center gap-2">
            <Link
              to="/plan"
              className="inline-flex min-h-12 items-center gap-2 rounded-full bg-saffron px-6 text-[15px] font-medium text-ink transition-colors duration-150 hover:bg-saffron-bright"
            >
              <MiraSparkle className="text-ink" /> Plan with Mira
            </Link>
            <Link
              to="/journeys"
              className="group inline-flex min-h-12 items-center gap-2 rounded-full px-4 text-[15px] text-on-dark underline-offset-4 hover:underline"
            >
              Explore journeys <ArrowRight className="size-4 transition-transform duration-150 group-hover:translate-x-0.5" aria-hidden />
            </Link>
          </div>
        </div>

        <div className="mt-auto grid min-w-0 grid-cols-[minmax(0,1fr)] items-end gap-6 pt-7 lg:grid-cols-[minmax(0,1fr)_360px]">
          <PromptBar className="w-full min-w-0 max-w-[760px]" />

          {/* Editorial caption + index */}
          <div className="order-first min-w-0 lg:order-none" role="group" aria-label="Choose a destination" onKeyDown={onKeys}>
            <div key={slide.id} className={cn("mb-4 hidden lg:block", !reduced && "animate-rise")} aria-live="polite">
              <div className={cn("h-px w-10", accentBg[slide.accent])} />
              <p className="mt-3 serif-italic text-2xl leading-tight">{slide.caption}</p>
              <p className="mt-2 text-xs tracking-wide text-on-dark/70">
                <span className={accentText[slide.accent]}>{slide.region}</span> · {slide.coords} · {slide.season}
              </p>
            </div>
            <ol className="scrollbar-none flex gap-1 overflow-x-auto lg:flex-row lg:flex-wrap lg:gap-x-3">
              {HERO_SLIDES.map((s, i) => {
                const isActive = i === active;
                return (
                  <li key={s.id} className="shrink-0">
                    <button
                      ref={(el) => {
                        controlsRef.current[i] = el;
                      }}
                      type="button"
                      onClick={() => go(i)}
                      aria-current={isActive ? "true" : undefined}
                      aria-label={`${s.index} ${s.name}, ${s.region}`}
                      tabIndex={isActive ? 0 : -1}
                      className={cn(
                        "group relative flex min-h-11 w-full items-center gap-3 rounded-full px-3 text-left transition-colors duration-150 lg:rounded-none lg:px-0",
                        isActive ? "text-on-dark" : "text-on-dark/55 hover:text-on-dark/90",
                      )}
                    >
                      <span className={cn("tabular text-[11px]", isActive && accentText[s.accent])}>{s.index}</span>
                      <span className="text-sm font-medium tracking-[-0.01em]">{s.name}</span>
                      {isActive && !reduced && !paused && (
                        <span className="absolute inset-x-0 top-0 hidden h-px overflow-hidden lg:block" aria-hidden>
                          <span
                            key={`${s.id}-bar`}
                            className={cn("block h-full origin-left", accentBg[s.accent])}
                            style={{ animation: `hero-progress ${AUTOPLAY_MS}ms linear both` }}
                          />
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ol>
          </div>
        </div>
      </div>
      <style>{`@keyframes hero-progress { from { transform: scaleX(0) } to { transform: scaleX(1) } }`}</style>
    </section>
  );
}

import { Link } from "@tanstack/react-router";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { useState, type KeyboardEvent } from "react";
import { EDITORIAL } from "@/lib/content";
import { photos } from "@/lib/photos";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { cn } from "@/lib/utils";

export function EditorialSlideshow() {
  const [i, setI] = useState(0);
  const reduced = useReducedMotion();
  const n = EDITORIAL.length;
  const slide = EDITORIAL[i]!;
  const flip = i % 2 === 1;
  const next = () => setI((v) => (v + 1) % n);
  const prev = () => setI((v) => (v - 1 + n) % n);
  const onKey = (e: KeyboardEvent) => {
    if (e.key === "ArrowRight") { e.preventDefault(); next(); }
    if (e.key === "ArrowLeft") { e.preventDefault(); prev(); }
  };

  return (
    <section
      data-nav-theme="light"
      aria-roledescription="carousel"
      aria-label="Stories from the island"
      className="bg-background py-6 md:py-10"
      onKeyDown={onKey}
    >
      <div className="mx-auto max-w-[1600px] px-3 md:px-5">
        <div className={cn("grid overflow-hidden rounded-photo bg-card md:grid-cols-2", flip && "md:[&>*:first-child]:order-2")}>
          <div className="relative aspect-[4/3] overflow-hidden md:aspect-auto md:min-h-[470px]">
            <img
              key={slide.id}
              src={photos[slide.photo].src}
              alt={photos[slide.photo].alt}
              loading="lazy"
              className={cn("absolute inset-0 h-full w-full object-cover", !reduced && "animate-mask-up")}
            />
          </div>
          <div className="flex flex-col justify-between gap-7 p-7 md:p-10 lg:p-14" aria-live="polite">
            <div className="flex items-center justify-between">
              <p className="eyebrow text-muted-foreground">Stories · {slide.place}</p>
              <p className="tabular text-sm text-muted-foreground">
                {String(i + 1).padStart(2, "0")} / {String(n).padStart(2, "0")}
              </p>
            </div>
            <div key={slide.id} className={cn("my-3", !reduced && "animate-rise")}>
              <h2 className="story-heading">
                <span className="font-semibold">{slide.title}</span>
              </h2>
              <p className="mt-6 max-w-md text-lg leading-relaxed text-muted-foreground">{slide.body}</p>
              <p className="mt-4 text-sm font-semibold text-maroon">{slide.detail}</p>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-4">
              <Link
                to="/plan"
                search={{ q: `I'd like to include ${slide.place}` }}
                className="inline-flex min-h-11 items-center rounded-full bg-primary px-6 text-sm font-semibold text-primary-foreground transition-colors duration-150 hover:bg-saffron-bright"
              >
                Add {slide.place} to a plan
              </Link>
              <div className="flex items-center gap-2">
                <button type="button" onClick={prev} aria-label="Previous story" className="grid size-11 place-items-center rounded-full border border-border transition-colors duration-150 hover:border-ink">
                  <ArrowLeft className="size-4" />
                </button>
                <button type="button" onClick={next} aria-label="Next story" className="grid size-11 place-items-center rounded-full border border-border transition-colors duration-150 hover:border-ink">
                  <ArrowRight className="size-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
        <div className="mx-auto mt-4 flex max-w-[1440px] gap-1.5 px-2" aria-hidden>
          {EDITORIAL.map((s, k) => (
            <span key={s.id} className={cn("h-[3px] flex-1 rounded-full transition-colors duration-150", k === i ? "bg-saffron" : "bg-border")} />
          ))}
        </div>
      </div>
    </section>
  );
}

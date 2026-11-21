import { Link } from "@tanstack/react-router";
import { ArrowUpRight } from "lucide-react";
import { useRef, useState, type KeyboardEvent } from "react";
import { STRIP } from "@/lib/content";
import { photos } from "@/lib/photos";
import { cn } from "@/lib/utils";
import { SectionHeading } from "./SectionHeading";

export function DestinationStrip() {
  const [active, setActive] = useState(0);
  const refs = useRef<Array<HTMLButtonElement | null>>([]);

  const onKey = (e: KeyboardEvent) => {
    const n = STRIP.length;
    let next: number | null = null;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = (active + 1) % n;
    if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = (active - 1 + n) % n;
    if (next !== null) {
      e.preventDefault();
      setActive(next);
      refs.current[next]?.focus();
    }
  };

  return (
    <section data-nav-theme="light" className="bg-background py-24 md:py-32">
      <div className="mx-auto max-w-[1440px] px-5 md:px-10">
        <div className="grid gap-6 md:grid-cols-[1.3fr_1fr] md:items-end">
          <SectionHeading eyebrow="Destinations" title="Find your kind of" italic="Sri Lanka." />
          <p className="max-w-sm text-muted-foreground md:justify-self-end">
            Five landscapes, a day's drive apart. Hover, tap or use the arrow keys to open each one.
          </p>
        </div>

        <div
          className="mt-12 flex h-[720px] flex-col gap-2.5 md:h-[580px] md:flex-row"
          role="group"
          aria-label="Destination strip"
          onKeyDown={onKey}
        >
          {STRIP.map((d, i) => {
            const isActive = i === active;
            const photo = photos[d.photo];
            return (
              <article
                key={d.id}
                onMouseEnter={() => setActive(i)}
                className={cn(
                  "group relative min-h-[72px] overflow-hidden rounded-photo bg-charcoal text-on-dark transition-[flex-grow] duration-500 ease-editorial",
                  isActive ? "flex-[4.2] md:flex-[3.4]" : "flex-1",
                )}
              >
                <img
                  src={photo.src}
                  alt={photo.alt}
                  loading="lazy"
                  className={cn(
                    "absolute inset-0 h-full w-full object-cover transition-[transform,filter] duration-700 ease-editorial",
                    isActive ? "scale-[1.04]" : "scale-100 brightness-[0.72]",
                  )}
                />
                <div className="absolute inset-0 bg-card-bottom" aria-hidden />
                <button
                  ref={(el) => {
                    refs.current[i] = el;
                  }}
                  type="button"
                  onClick={() => setActive(i)}
                  onFocus={() => setActive(i)}
                  aria-expanded={isActive}
                  aria-label={`${d.name}: ${d.subtitle}`}
                  className="absolute inset-0 z-10 rounded-photo"
                />
                <div className="pointer-events-none absolute inset-x-0 bottom-0 z-20 p-5 md:p-7">
                  <span className="tabular text-xs text-on-dark/70">0{i + 1}</span>
                  <h3 className={cn("mt-1 font-semibold tracking-[-0.04em] transition-[font-size] duration-300", isActive ? "text-3xl md:text-5xl" : "text-lg md:text-xl")}>
                    {d.name}
                  </h3>
                  <div className={cn("grid transition-[grid-template-rows,opacity] duration-500 ease-editorial", isActive ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0")}>
                    <div className="overflow-hidden">
                      <p className="mt-2 max-w-sm text-sm text-on-dark/80 md:text-base">{d.subtitle}</p>
                      <Link
                        to="/plan"
                        search={{ q: d.brief }}
                        tabIndex={isActive ? 0 : -1}
                        className="pointer-events-auto mt-4 inline-flex min-h-11 items-center gap-1.5 rounded-full bg-on-dark px-5 text-sm font-medium text-ink transition-colors duration-150 hover:bg-saffron"
                      >
                        Explore {d.name} <ArrowUpRight className="size-4" aria-hidden />
                      </Link>
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

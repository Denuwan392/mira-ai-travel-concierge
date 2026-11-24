import { Link } from "@tanstack/react-router";
import { ArrowUpRight } from "lucide-react";
import { usePublished } from "@/lib/live/published";
import { photos } from "@/lib/photos";
import { cn } from "@/lib/utils";
import { SectionHeading } from "./SectionHeading";

const LAYOUT = [
  "md:col-span-5 md:row-span-2 aspect-[4/5] md:aspect-auto",
  "md:col-span-7 aspect-[16/10] md:aspect-auto",
  "md:col-span-4 aspect-[4/5] md:aspect-auto",
  "md:col-span-3 aspect-[4/5] md:aspect-auto",
  "md:col-span-12 aspect-[16/9] md:aspect-auto",
];

export function FeaturedJourneys({ showHeading = true }: { showHeading?: boolean }) {
  const {items,status}=usePublished();
  const ordered=[...items].sort((a,b)=>Number(["T01","T09","T05","T04","T11"].includes(b.id))-Number(["T01","T09","T05","T04","T11"].includes(a.id)));
  return (
    <section data-nav-theme="light" className="bg-background py-24 md:py-32">
      <div className="mx-auto max-w-[1440px] px-5 md:px-10">
        {showHeading && (
          <div className="flex flex-wrap items-end justify-between gap-6">
            <SectionHeading eyebrow="Featured journeys" title="Starting points," italic="not set menus." />
            <Link to="/journeys" className="inline-flex min-h-11 items-center gap-1.5 rounded-full border border-ink/20 px-5 text-sm hover:border-ink">
              All journeys <ArrowUpRight className="size-4" aria-hidden />
            </Link>
          </div>
        )}
        <div className={cn("grid gap-4 md:grid-flow-dense md:grid-cols-12 md:auto-rows-[260px]", showHeading && "mt-14")}>
          {status && <p role="status">{status}</p>}
          {(showHeading?ordered.slice(0,5):ordered).map((j, i) => (
            <Link
              key={j.id}
              to="/plan"
              search={{ q: "@tour "+j.id }}
              className={cn("group relative block overflow-hidden rounded-photo bg-charcoal text-on-dark", LAYOUT[i % LAYOUT.length])}
            >
              <img
                src={photos[j.photo].src}
                alt={photos[j.photo].alt}
                loading="lazy"
                className="absolute inset-0 h-full w-full object-cover transition-transform duration-150 ease-editorial group-hover:scale-[1.04]"
              />
              <div className="absolute inset-0 bg-card-bottom" aria-hidden />
              <div className="absolute inset-x-0 top-0 flex items-start justify-between p-5">
                <span className="rounded-full bg-on-dark px-3 py-1 text-xs font-semibold text-ink">{j.category}</span>
                <span className="tabular rounded-full border border-on-dark/40 px-3 py-1 text-xs">{j.duration}</span>
              </div>
              <div className="absolute inset-x-0 bottom-0 p-5 md:p-6">
                <h3 className="text-2xl font-semibold tracking-[-0.035em] md:text-3xl">{j.title}</h3>
                <p className="mt-2 text-sm text-on-dark/75">
                  {j.places.map((r, k) => (
                    <span key={r}>
                      {k > 0 && <span className="mx-1.5 text-saffron">→</span>}
                      {r}
                    </span>
                  ))}
                </p>
                <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100">
                  Shape this with Mira <ArrowUpRight className="size-4" aria-hidden />
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

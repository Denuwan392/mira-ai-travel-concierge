import { useEffect, useState, type FocusEvent } from "react";
import { ChevronLeft, ChevronRight, ArrowRight } from "lucide-react";
import { photos } from "@/lib/photos";

export interface DestinationSlide {
  slug: string;
  name: string;
  tagline: string;
  src: string;
  alt: string;
}

const DEFAULT_SLIDES: DestinationSlide[] = [
  {
    slug: "sigiriya",
    name: "Sigiriya",
    tagline: "Ancient wonders",
    src: photos.sigiriya.src,
    alt: photos.sigiriya.alt,
  },
  {
    slug: "ella",
    name: "Ella",
    tagline: "Journey through the highlands",
    src: photos.ella.src,
    alt: photos.ella.alt,
  },
  {
    slug: "galle",
    name: "Galle",
    tagline: "Coastal heritage",
    src: photos.galle.src,
    alt: photos.galle.alt,
  },
  {
    slug: "yala",
    name: "Yala",
    tagline: "Into the wild",
    src: photos.yala.src,
    alt: photos.yala.alt,
  },
  {
    slug: "mirissa",
    name: "Mirissa",
    tagline: "Escape to the coast",
    src: photos.mirissa.src,
    alt: photos.mirissa.alt,
  },
];

export interface DestinationShowcaseProps {
  onExplore: () => void;
  destinations?: { slug?: string; title?: string }[];
  autoPlay?: boolean;
  intervalMs?: number;
}

export function DestinationShowcase({
  onExplore,
  destinations,
  autoPlay = true,
  intervalMs = 5000,
}: DestinationShowcaseProps) {
  const slides: DestinationSlide[] = DEFAULT_SLIDES.map((slide) => {
    const matched = destinations?.find((d) => d.slug === slide.slug);
    return matched?.title ? { ...slide, name: matched.title } : slide;
  });

  const [activeIndex, setActiveIndex] = useState(0);
  const [loadedIndices, setLoadedIndices] = useState<number[]>([0]);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() => {
    if (typeof window === "undefined" || !window.matchMedia) return false;
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  });
  const [userPaused, setUserPaused] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [isFocusedWithin, setIsFocusedWithin] = useState(false);
  const [isPageVisible, setIsPageVisible] = useState(() => {
    if (typeof document === "undefined") return true;
    return document.visibilityState !== "hidden";
  });
  const [failedSlugs, setFailedSlugs] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mq.addEventListener?.("change", onChange);
    return () => mq.removeEventListener?.("change", onChange);
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const onVisibility = () => setIsPageVisible(document.visibilityState !== "hidden");
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  const isEffectivePlaying =
    autoPlay && !prefersReducedMotion && !userPaused && !isHovered && !isFocusedWithin && isPageVisible;

  useEffect(() => {
    if (!isEffectivePlaying) return;
    const timer = window.setInterval(() => {
      setActiveIndex((prev) => {
        const next = (prev + 1) % slides.length;
        setLoadedIndices((cur) => (cur.includes(next) ? cur : [...cur, next]));
        return next;
      });
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [isEffectivePlaying, intervalMs, slides.length]);

  const activeSlide: DestinationSlide = (slides[activeIndex] ?? slides[0] ?? DEFAULT_SLIDES[0]) as DestinationSlide;

  const goTo = (index: number) => {
    const next = (index + slides.length) % slides.length;
    setLoadedIndices((cur) => (cur.includes(next) ? cur : [...cur, next]));
    setActiveIndex(next);
  };

  const handleBlur = (e: FocusEvent<HTMLDivElement>) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
      setIsFocusedWithin(false);
    }
  };

  const isCurrentFailed = Boolean(failedSlugs[activeSlide.slug]);
  const displayName = isCurrentFailed ? "Sri Lanka" : activeSlide.name;
  const displayTagline = isCurrentFailed ? "Island landscapes" : activeSlide.tagline;

  return (
    <section
      aria-label="Sri Lanka destination showcase"
      className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-16"
    >
      <div
        className="bg-[#F26B1D] rounded-[12px] p-6 sm:p-8 lg:p-10 overflow-hidden"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onFocus={() => setIsFocusedWithin(true)}
        onBlur={handleBlur}
      >
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-10 items-center">
          {/* Photography (~58% on desktop) */}
          <div className="lg:col-span-7">
            <div className="relative rounded-[12px] overflow-hidden bg-[#111111]/10 aspect-[16/10] w-full">
              {slides.map((slide, idx) => {
                if (!loadedIndices.includes(idx)) return null;
                const isActive = idx === activeIndex;
                const failed = Boolean(failedSlugs[slide.slug]);
                return (
                  <img
                    key={slide.slug}
                    src={failed ? photos.landscapeArch.src : slide.src}
                    alt={failed ? photos.landscapeArch.alt : slide.alt}
                    loading={idx === 0 ? "eager" : "lazy"}
                    decoding="async"
                    aria-hidden={!isActive}
                    onError={() => setFailedSlugs((prev) => ({ ...prev, [slide.slug]: true }))}
                    className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-150 ${
                      isActive ? "opacity-100 z-10" : "opacity-0 z-0 pointer-events-none"
                    }`}
                  />
                );
              })}
              <div className="absolute bottom-3 left-3 right-3 z-20 flex items-center justify-between gap-2">
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-[999px] bg-[#111111]/85 text-white text-xs font-medium">
                  <span className="font-semibold">{displayName}</span>
                  <span aria-hidden="true" className="text-white/60">
                    —
                  </span>
                  <span className="text-white/90">{displayTagline}</span>
                </div>
                <span className="px-2.5 py-1 rounded-[999px] bg-[#111111]/85 text-white text-[11px] font-medium tabular-nums">
                  {activeIndex + 1} / {slides.length}
                </span>
              </div>
            </div>
          </div>

          {/* Editorial Content (~42% on desktop) */}
          <div className="lg:col-span-5 flex flex-col justify-between space-y-6">
            <div className="space-y-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-[#111111]/85">
                DISCOVER THE ISLAND
              </p>
              <h2 className="text-3xl sm:text-4xl lg:text-[42px] font-bold text-[#111111] leading-[1.12] tracking-tight">
                One island. Endless journeys.
              </h2>
              <p className="text-sm sm:text-base text-[#111111]/90 leading-relaxed max-w-md">
                From misty mountains to golden coastlines. Discover Sri Lanka at your own pace.
              </p>
              <div className="pt-1">
                <button
                  type="button"
                  onClick={onExplore}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-[999px] bg-[#111111] text-white text-sm font-semibold hover:bg-[#111111]/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#111111] transition-colors duration-150 cursor-pointer"
                >
                  <span>Explore journeys</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Subtle accessible rotation controls */}
            <div className="flex items-center justify-between gap-3 pt-4 border-t border-[#111111]/15">
              <div className="flex items-center gap-1.5" role="group" aria-label="Destination pagination">
                {slides.map((slide, idx) => {
                  const isActive = idx === activeIndex;
                  return (
                    <button
                      key={slide.slug}
                      type="button"
                      onClick={() => goTo(idx)}
                      aria-label={`Show ${slide.name}`}
                      aria-current={isActive ? "true" : undefined}
                      className={`h-2 rounded-[999px] transition-all duration-150 cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#111111] ${
                        isActive ? "w-6 bg-[#111111]" : "w-2 bg-[#111111]/35 hover:bg-[#111111]/60"
                      }`}
                    />
                  );
                })}
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setUserPaused((p) => !p)}
                  aria-label={userPaused ? "Resume destination rotation" : "Pause destination rotation"}
                  aria-pressed={userPaused}
                  className="sr-only focus:not-sr-only focus:px-2.5 focus:py-1 focus:rounded-[999px] focus:bg-[#111111] focus:text-white focus:text-xs focus:font-medium"
                >
                  {userPaused ? "Resume" : "Pause"}
                </button>
                <button
                  type="button"
                  onClick={() => goTo(activeIndex - 1)}
                  aria-label="Previous destination"
                  className="w-9 h-9 rounded-full bg-[#111111]/15 hover:bg-[#111111]/25 text-[#111111] flex items-center justify-center transition-colors duration-150 cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#111111]"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => goTo(activeIndex + 1)}
                  aria-label="Next destination"
                  className="w-9 h-9 rounded-full bg-[#111111] hover:bg-[#111111]/90 text-white flex items-center justify-center transition-colors duration-150 cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#111111]"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

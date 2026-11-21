import { cn } from "@/lib/utils";

/** Mira's mark: a four-point saffron compass sparkle. */
export function MiraSparkle({ className, animated = false, title }: { className?: string | undefined; animated?: boolean | undefined; title?: string | undefined }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={cn("size-4 shrink-0 text-saffron", animated && "animate-sparkle", className)}
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
    >
      <path
        fill="currentColor"
        d="M12 0c.6 6.6 4.8 10.8 12 12-7.2 1.2-11.4 5.4-12 12-.6-6.6-4.8-10.8-12-12C7.2 10.8 11.4 6.6 12 0Z"
      />
    </svg>
  );
}

export function MiraAvatar({ className, animated }: { className?: string | undefined; animated?: boolean | undefined }) {
  return (
    <span className={cn("grid size-8 shrink-0 place-items-center rounded-full bg-ink", className)} aria-hidden>
      <MiraSparkle className="size-3.5" animated={animated} />
    </span>
  );
}

import { useNavigate } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { type FormEvent } from "react";
import { STARTERS } from "@/lib/content";
import { cn } from "@/lib/utils";
import { MiraSparkle } from "./MiraSparkle";

type Props = { tone?: "light" | "dark"; showStarters?: boolean; className?: string; id?: string };

export function PromptBar({ tone = "light", showStarters = true, className, id = "mira-prompt" }: Props) {
  const navigate = useNavigate();


  const go = (q: string) => navigate({ to: "/plan", search: { q } });
  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const brief = String(new FormData(e.currentTarget).get("q") ?? "").trim();
    void go(brief);
  };

  return (
    <div className={cn("rounded-[26px] bg-card p-2 text-ink shadow-float", tone === "dark" && "shadow-none", className)}>
      <form action="/plan" method="get" onSubmit={submit} className="flex items-center gap-2" role="search" aria-label="Describe your trip to Mira">
        <span className="hidden pl-3 sm:block">
          <MiraSparkle className="size-5" />
        </span>
        <label htmlFor={id} className="sr-only">
          Where would you like Sri Lanka to take you?
        </label>
        <input
          name="q"
          id={id}
          maxLength={1200}
          placeholder="Where would you like Sri Lanka to take you? e.g. 10 days, tea country, leopards, a quiet beach"
          className="min-h-12 min-w-0 flex-1 bg-transparent px-3 text-[15px] placeholder:text-muted-foreground focus:outline-none sm:text-base"
          autoComplete="off"
        />
        <button
          type="submit"
          className="inline-flex min-h-12 shrink-0 items-center gap-2 rounded-full bg-ink px-5 text-sm font-medium text-on-dark transition-colors duration-150 hover:bg-charcoal-soft"
        >
          <span className="hidden sm:inline">Ask Mira</span>
          <ArrowRight aria-hidden className="size-4" />
          <span className="sr-only sm:hidden">Ask Mira</span>
        </button>
      </form>
      {showStarters && (
        <div className="scrollbar-none -mx-0.5 mt-1.5 flex gap-1.5 overflow-x-auto px-0.5 pb-0.5" aria-label="Quick starters">
          {STARTERS.map((s) => (
            <button
              key={s.label}
              type="button"
              onClick={() => go(s.brief)}
              className="inline-flex min-h-11 shrink-0 items-center rounded-full border border-border px-4 text-[13px] text-ink/80 transition-colors duration-150 hover:border-ink hover:text-ink"
            >
              {s.label === "Surprise Me" && <MiraSparkle className="mr-1.5 size-3" />}
              {s.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

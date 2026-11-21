import { Link } from "@tanstack/react-router";
import { cn } from "@/lib/utils";

export function Logo({ className }: { className?: string }) {
  return (
    <Link to="/" className={cn("group inline-flex min-h-11 items-center gap-2.5 rounded-full", className)} aria-label="Ceylon Compass Holidays — home">
      <img className="company-logo" src="/ceylon-compass.png" alt="" />
      <span className="flex flex-col leading-none">
        <span className="text-[17px] font-semibold tracking-[-0.03em]">
          Ceylon <span className="serif-italic text-[19px]">Compass</span>
        </span>
        <span className="eyebrow mt-1 text-[9px] opacity-60">Holidays</span>
      </span>
    </Link>
  );
}

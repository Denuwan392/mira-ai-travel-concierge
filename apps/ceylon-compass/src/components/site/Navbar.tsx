import { Link, useRouterState } from "@tanstack/react-router";
import { Menu } from "lucide-react";
import { useEffect, useState } from "react";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";

import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";
import { Logo } from "./Logo";
import { MiraSparkle } from "./MiraSparkle";
import { NAV_LINKS } from "./nav-links";

type NavTheme = "hero" | "dark" | "light";

function useNavTheme(pathname: string): NavTheme {
  const [theme, setTheme] = useState<NavTheme>(pathname === "/" ? "hero" : "light");
  useEffect(() => {
    const probe = 36;
    const update = () => {
      let next: NavTheme = "light";
      document.querySelectorAll<HTMLElement>("[data-nav-theme]").forEach((el) => {
        const r = el.getBoundingClientRect();
        if (r.top <= probe && r.bottom > probe) next = (el.dataset["navTheme"] as NavTheme) ?? "light";
      });
      setTheme(next);
    };
    update();
    const raf = requestAnimationFrame(update);
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [pathname]);
  return theme;
}

export function Navbar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const theme = useNavTheme(pathname);
  const { user, isAuthenticated, isStaff } = useAuth();

  const [open, setOpen] = useState(false);
  const onDark = theme !== "light";

  useEffect(() => setOpen(false), [pathname]);

  return (
    <header
      data-theme={theme}
      className={cn(
        "fixed inset-x-0 top-0 z-50 transition-[background-color,color,border-color] duration-150",
        theme === "hero" && "border-b border-transparent bg-transparent text-on-dark",
        theme === "dark" && "border-b border-line-dark bg-charcoal text-on-dark",
        theme === "light" && "border-b border-border bg-paper text-ink",
      )}
    >
      <nav aria-label="Main" className="mx-auto flex h-[72px] max-w-[1440px] items-center justify-between gap-6 px-5 md:px-10">
        <Logo />
        <ul className="hidden items-center gap-1 xl:flex">
          {NAV_LINKS.map((l) => (
            <li key={l.to}>
              <Link
                to={l.to}
                className={cn(
                  "inline-flex min-h-11 items-center rounded-full px-3.5 text-sm transition-colors duration-150",
                  onDark ? "text-on-dark/80 hover:text-on-dark" : "text-ink/70 hover:text-ink",
                )}
                activeProps={{ className: onDark ? "!text-on-dark" : "!text-ink font-semibold" }}
              >
                {l.label}
              </Link>
            </li>
          ))}
        </ul>
        <div className="flex items-center gap-1.5">
          <Link
            to="/plan"
            className={cn(
              "hidden min-h-11 items-center gap-2 rounded-full px-4 text-sm font-semibold transition-colors duration-150 md:inline-flex",
              onDark ? "hover:bg-on-dark/10" : "hover:bg-paper-deep",
            )}
          >
            <MiraSparkle /> Ask Mira
          </Link>
          <Link
            to="/trips"
            className={cn(
              "hidden min-h-11 items-center rounded-full px-4 text-sm transition-colors duration-150 md:inline-flex",
              onDark ? "text-on-dark/80 hover:text-on-dark" : "text-ink/70 hover:text-ink",
            )}
          >
            My Trips
          </Link>
          <Link
            to="/quotes"
            className={cn(
              "hidden min-h-11 items-center rounded-full px-4 text-sm transition-colors duration-150 lg:inline-flex",
              onDark ? "text-on-dark/80 hover:text-on-dark" : "text-ink/70 hover:text-ink",
            )}
          >
            My Quotes
          </Link>
          {isStaff && (
            <Link
              to="/staff"
              className={cn(
                "hidden min-h-11 items-center rounded-full px-4 text-sm font-semibold transition-colors duration-150 md:inline-flex",
                onDark ? "text-saffron hover:bg-on-dark/10" : "text-amber-700 hover:bg-paper-deep",
              )}
            >
              Staff Console
            </Link>
          )}
          {isAuthenticated ? (
            <Link
              to="/profile"
              className={cn(
                "hidden min-h-11 items-center rounded-full border px-5 text-sm font-semibold transition-colors duration-150 sm:inline-flex",
                onDark ? "border-on-dark/35 hover:border-on-dark hover:bg-on-dark/10" : "border-ink/20 hover:border-ink",
              )}
            >
              {user?.full_name ? user.full_name.split(" ")[0] : "Profile"}
            </Link>
          ) : (
            <Link
              to="/login"
              className={cn(
                "hidden min-h-11 items-center rounded-full border px-5 text-sm font-semibold transition-colors duration-150 sm:inline-flex",
                onDark ? "border-on-dark/35 hover:border-on-dark hover:bg-on-dark/10" : "border-ink/20 hover:border-ink",
              )}
            >
              Sign In
            </Link>
          )}
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <button
                type="button"
                className={cn(
                  "grid size-11 place-items-center rounded-full xl:hidden",
                  onDark ? "hover:bg-on-dark/10" : "hover:bg-paper-deep",
                )}
                aria-label="Open menu"
              >
                <Menu className="size-5" />
              </button>
            </SheetTrigger>
            <SheetContent side="right" className="w-full max-w-sm border-l-0 bg-charcoal p-0 text-on-dark">
              <MobileNav />
            </SheetContent>
          </Sheet>
        </div>
      </nav>
    </header>
  );
}

/** Reusable full-screen mobile navigation. */
export function MobileNav() {
  const { user, isAuthenticated, isStaff } = useAuth();

  return (
    <div className="flex h-full flex-col px-7 pt-8 pb-safe">
      <SheetTitle className="eyebrow text-on-dark-muted">Menu</SheetTitle>
      <ul className="mt-8 space-y-1">
        {NAV_LINKS.map((l, i) => (
          <li key={l.to}>
            <Link to={l.to} className="flex min-h-12 items-baseline gap-4 rounded-full text-2xl font-semibold tracking-[-0.04em]">
              <span className="tabular w-6 text-xs font-normal text-on-dark-muted">0{i + 1}</span>
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
      <div className="mt-auto space-y-2 pt-10">
        <Link to="/plan" className="flex min-h-12 items-center justify-center gap-2 rounded-full bg-saffron font-semibold text-ink">
          <MiraSparkle className="text-ink" /> Ask Mira
        </Link>
        <div className="grid grid-cols-2 gap-2">
          <Link to="/trips" className="flex min-h-12 items-center justify-center rounded-full border border-line-dark">
            My Trips
          </Link>
          <Link to="/quotes" className="flex min-h-12 items-center justify-center rounded-full border border-line-dark">
            My Quotes
          </Link>
          {isAuthenticated ? (
            <Link to="/profile" className="flex min-h-12 items-center justify-center rounded-full border border-line-dark">
              {user?.full_name ? user.full_name.split(" ")[0] : "Profile"}
            </Link>
          ) : (
            <Link to="/login" className="flex min-h-12 items-center justify-center rounded-full border border-line-dark font-semibold text-saffron">
              Sign In
            </Link>
          )}
          {isStaff ? (
            <Link to="/staff" className="flex min-h-12 items-center justify-center rounded-full border border-line-dark">
              Staff Console
            </Link>
          ) : !isAuthenticated ? (
            <Link to="/register" className="flex min-h-12 items-center justify-center rounded-full border border-line-dark">
              Register
            </Link>
          ) : null}
        </div>
      </div>
    </div>
  );
}

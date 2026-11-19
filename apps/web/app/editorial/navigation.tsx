"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { ArrowUpRight, Menu, X, User } from "lucide-react";
import { BrandMark } from "../brand";

const NAV_LINKS = [
  { href: "/#explore",   label: "Explore" },
  { href: "/plan#destinations", label: "Destinations" },
  { href: "/plan",       label: "Plan with Mira" },
  { href: "/my-trips",   label: "My Trips" },
] as const;

export function FloatingNav() {
  const pathname = usePathname();
  const [open, setOpen]       = useState(false);
  const [scrolled, setScrolled] = useState(false);

  const close = () => setOpen(false);
  const isHome = pathname === "/";

  /* Subtle scroll-shadow lift */
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 18);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={[
        "mast",
        isHome ? "mast-home" : "",
        scrolled ? "mast-scrolled" : "",
      ].join(" ").trim()}
      onKeyDown={e => {
        if (e.key === "Escape") {
          close();
          (document.getElementById("menu-toggle") as HTMLButtonElement | null)?.focus();
        }
      }}
    >
      <div className="mast-inner">
        {/* ── Logo ── */}
        <Link prefetch={false} href="/" className="wordmark" onClick={close} aria-label="MIRA — Ceylon Compass Holidays home">
          <BrandMark />
          <span>
            Ceylon Compass
            <small>Holidays</small>
          </span>
        </Link>

        {/* ── Desktop nav ── */}
        <nav
          id="mast-links"
          className={open ? "nav-open" : ""}
          aria-label="Main navigation"
        >
          {NAV_LINKS.map(({ href, label }) => (
            <Link prefetch={false}
              key={href}
              href={href}
              onClick={close}
              aria-current={pathname === href ? "page" : undefined}
            >
              {label}
            </Link>
          ))}
        </nav>

        {/* ── Account button ── */}
        <Link prefetch={false}
          href="/my-trips"
          onClick={close}
          className="lux-action action-light mast-account"
          aria-label="Account, saved trips"
          style={{ gap: 8, padding: "9px 16px 9px 12px" }}
        >
          <User size={15} strokeWidth={1.8} />
          <span className="mast-account-label">Account</span>
        </Link>

        {/* ── CTA ── */}
        <Link prefetch={false}
          href="/plan"
          onClick={close}
          className="lux-action mast-cta"
        >
          Plan a trip
          <ArrowUpRight size={15} />
        </Link>

        {/* ── Hamburger ── */}
        <button
          id="menu-toggle"
          className="menu-toggle"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-controls="mast-links"
          aria-expanded={open}
          onClick={() => setOpen(o => !o)}
        >
          {open ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>

      {/* Inline styles for elements not covered by editorial.css */}
      <style>{`
        .mast-account-label { font-size: 13px; font-weight: 600; }
        .mast-scrolled .mast-inner {
          box-shadow: 0 10px 40px rgba(10,33,23,.18), 0 1px 0 rgba(255,255,255,.6) inset;
        }
        @media (max-width: 740px) {
          .mast-account { display: none; }
          .mast-cta { margin-left: auto; }
        }
        @media (max-width: 480px) {
          .mast-cta span { display: none; }
        }
      `}</style>
    </header>
  );
}

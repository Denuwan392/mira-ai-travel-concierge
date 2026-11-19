"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { ArrowUpRight, Menu, X } from "lucide-react";
import { BrandMark } from "../brand";

export function FloatingNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);
  return <header className={`mast ${pathname === "/" ? "mast-home" : ""}`} onKeyDown={e => { if (e.key === "Escape") { close(); document.getElementById("menu-toggle")?.focus(); } }}>
    <div className="mast-inner">
      <Link href="/" className="wordmark" onClick={close}><BrandMark /><span>Ceylon Compass<small>HOLIDAYS</small></span></Link>
      <nav id="mast-links" className={open ? "nav-open" : ""} aria-label="Main navigation">
        <Link onClick={close} href="/#explore">Explore journeys</Link>
        <Link onClick={close} href="/#how">Meet Mira</Link>
        <Link onClick={close} href="/my-trips">My trips</Link>
      </nav>
      <Link href="/plan" onClick={close} className="lux-action mast-cta">Plan a trip <ArrowUpRight size={15}/></Link>
      <button id="menu-toggle" className="menu-toggle" aria-label={open ? "Close menu" : "Open menu"} aria-controls="mast-links" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? <X/> : <Menu/>}</button>
    </div>
  </header>;
}

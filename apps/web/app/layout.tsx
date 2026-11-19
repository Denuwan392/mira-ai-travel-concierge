import type { Metadata } from "next";
import Link from "next/link";
import { BrandMark } from "./brand";
import "./style.css";

export const metadata: Metadata = {
  title: "Mira | Ceylon Compass Holidays",
  description: "Explore Sri Lanka, your way, with Mira, your personal travel companion.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>
        <header className="topbar">
          <div className="frame header-inner">
            <Link href="/" className="wordmark" aria-label="Ceylon Compass Holidays home">
              <BrandMark /><span>Ceylon Compass<small>HOLIDAYS</small></span>
            </Link>
            <nav aria-label="Main navigation">
              <Link href="/#explore">Explore</Link>
              <Link href="/#how">How it works</Link>
              <Link href="/my-trips">My trips</Link>
            </nav>
            <Link href="/plan" className="button dark header-cta">Plan a trip</Link>
          </div>
        </header>
        {children}
        <footer className="frame footer"><Link className="wordmark" href="/"><BrandMark size={24} /> Ceylon Compass</Link>
          <span>Fictional travel concierge · Demo booking only</span><Link href="/staff">Staff console</Link>
        </footer>
      </body>
    </html>
  );
}

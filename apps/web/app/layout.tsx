import type { Metadata } from "next";
import Link from "next/link";
import { BrandMark } from "./brand";
import { FloatingNav } from "./editorial/navigation";
import { MiraShell } from "./plan/mira-shell";
import "./style.css";
import "./editorial.css";
import "./plan/advisor.css";
import "./mira-shell.css";

export const metadata: Metadata = {
  title: "Mira | Ceylon Compass Holidays",
  description: "Explore Sri Lanka, your way, with Mira, your personal travel companion.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <MiraShell><FloatingNav />
        {children}
        <footer className="frame footer"><Link prefetch={false} className="wordmark" href="/"><BrandMark size={24} /> Ceylon Compass</Link>
          <span>Fictional travel concierge · Demo booking only</span><Link prefetch={false} href="/credits">Photography</Link><Link prefetch={false} href="/staff">Staff console</Link>
        </footer></MiraShell>
      </body>
    </html>
  );
}

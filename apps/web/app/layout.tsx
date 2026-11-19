import type { Metadata } from "next";
import Link from "next/link";
import { BrandMark } from "./brand";
import { FloatingNav } from "./editorial/navigation";
import "./style.css";
import "./editorial.css";

export const metadata: Metadata = {
  title: "Mira | Ceylon Compass Holidays",
  description: "Explore Sri Lanka, your way, with Mira, your personal travel companion.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <FloatingNav />
        {children}
        <footer className="frame footer"><Link className="wordmark" href="/"><BrandMark size={24} /> Ceylon Compass</Link>
          <span>Fictional travel concierge · Demo booking only</span><Link href="/credits">Photography</Link><Link href="/staff">Staff console</Link>
        </footer>
      </body>
    </html>
  );
}

import { Link } from "@tanstack/react-router";
import { Logo } from "./Logo";
import { NAV_LINKS } from "./nav-links";

export function Footer() {
  return (
    <footer data-nav-theme="dark" className="bg-charcoal text-on-dark">
      <div className="mx-auto grid max-w-[1440px] gap-10 border-t border-line-dark px-5 py-14 md:grid-cols-[1.4fr_2fr] md:px-10">
        <div>
          <Logo />
          <p className="mt-5 max-w-xs text-sm text-on-dark-muted">
            A Sri Lankan travel concierge. Mira sketches the journey; a human specialist confirms every detail.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-8 text-sm sm:grid-cols-3">
          <ul className="space-y-1">
            {NAV_LINKS.map((l) => (
              <li key={l.to}>
                <Link to={l.to} className="inline-flex min-h-11 items-center text-on-dark-muted hover:text-on-dark">{l.label}</Link>
              </li>
            ))}
          </ul>
          <ul className="space-y-1">
            <li><Link to="/plan" className="inline-flex min-h-11 items-center text-on-dark-muted hover:text-on-dark">Ask Mira</Link></li>
            <li><Link to="/trips" className="inline-flex min-h-11 items-center text-on-dark-muted hover:text-on-dark">My Trips</Link></li>
            <li><Link to="/sign-in" className="inline-flex min-h-11 items-center text-on-dark-muted hover:text-on-dark">Visitor profile</Link></li>
          </ul>
          <a className="inline-flex min-h-11 items-center" href="http://127.0.0.1:3000/staff">Staff console ↗</a>
          <p className="col-span-2 text-xs leading-relaxed text-on-dark-muted sm:col-span-1">
            Private trip notebooks and enquiries are saved with Mira. Bookings and payments are simulated.
          </p>
        </div>
      </div>
      <div className="mx-auto flex max-w-[1440px] flex-wrap justify-between gap-3 px-5 pb-8 text-xs text-on-dark-muted md:px-10">
        <span>© {new Date().getFullYear()} Ceylon Compass Holidays</span>
        <span className="serif-italic text-sm">Sri Lanka, without limits.</span>
      </div>
    </footer>
  );
}

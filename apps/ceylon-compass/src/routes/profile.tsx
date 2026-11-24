import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";
import { api, session } from "@/lib/live/service";

export const Route = createFileRoute("/profile")({
  component: ProfilePage,
});

type UserProfile = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  status: string;
  phone: string;
  preferences: Record<string, string>;
  created_at: string;
};

type QuoteSummary = {
  id: string;
  title: string;
  date: string;
  total: number;
  deposit: number;
  adults: number;
  ages: number[];
  current: boolean;
  created: string;
};

type TravellerEnquiry = {
  id: string;
  reference?: string;
  reason: string;
  human_reason?: string;
  status: string;
  trip: string;
  trip_id?: string | null;
  tour_name?: string;
  travel_date?: string | null;
  adults?: number | null;
  children_count?: number;
  quoted_total_usd?: number | null;
  created: string;
};

type OverviewData = {
  user: UserProfile;
  last_quote: QuoteSummary | null;
  total_quotes: number;
  total_enquiries: number;
  active_enquiries?: number;
  total_trips?: number;
  enquiries: TravellerEnquiry[];
  trips: { id: string; title: string; updated: string }[];
};

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [rememberBrowser, setRememberBrowser] = useState(false);

  // Edit profile state
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [dietary, setDietary] = useState("");
  const [travelPace, setTravelPace] = useState("");
  const [profileMsg, setProfileMsg] = useState("");
  const [profileBusy, setProfileBusy] = useState(false);

  // Password change state
  const [currPassword, setCurrPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [pwdMsg, setPwdMsg] = useState("");
  const [pwdBusy, setPwdBusy] = useState(false);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        await session();
        const sess = await api<{ remember: boolean }>("/session");
        setRememberBrowser(sess.remember);

        const me = await api<UserProfile>("/auth/me");
        setUser(me);
        setFullName(me.full_name);
        setPhone(me.phone || "");
        setDietary(me.preferences?.["dietary"] || "");
        setTravelPace(me.preferences?.["pace"] || "");

        const ov = await api<OverviewData>("/traveller/overview");
        setOverview(ov);
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  async function handleProfileUpdate(e: FormEvent) {
    e.preventDefault();
    setProfileBusy(true);
    setProfileMsg("");
    try {
      const updated = await api<UserProfile>("/auth/profile", {
        method: "PATCH",
        body: JSON.stringify({
          full_name: fullName,
          phone,
          preferences: { dietary, pace: travelPace },
        }),
      });
      setUser(updated);
      window.dispatchEvent(new CustomEvent("cch:auth", { detail: updated }));
      setProfileMsg("Profile preferences saved successfully.");
    } catch (err) {
      setProfileMsg(err instanceof Error ? err.message : "Failed to update profile.");
    } finally {
      setProfileBusy(false);
    }
  }

  async function handlePasswordChange(e: FormEvent) {
    e.preventDefault();
    if (newPassword.length < 8) {
      setPwdMsg("New password must be at least 8 characters.");
      return;
    }
    setPwdBusy(true);
    setPwdMsg("");
    try {
      await api("/auth/password", {
        method: "POST",
        body: JSON.stringify({
          current_password: currPassword,
          new_password: newPassword,
        }),
      });
      setPwdMsg("Password updated successfully. Other active sessions revoked.");
      setCurrPassword("");
      setNewPassword("");
    } catch (err) {
      setPwdMsg(err instanceof Error ? err.message : "Password change failed.");
    } finally {
      setPwdBusy(false);
    }
  }

  async function handleLogout() {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      // Ignore network errors
    } finally {
      setUser(null);
      window.dispatchEvent(new CustomEvent("cch:auth", { detail: null }));
      router.navigate({ to: "/login" });
    }
  }

  if (loading) {
    return (
      <main className="folio">
        <p className="eyebrow">Traveller notebook</p>
        <h1>Loading account…</h1>
        <p>Retrieving your saved journeys and preferences.</p>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="folio">
        <p className="eyebrow">Traveller account</p>
        <h1>Your travel profile</h1>
        <p>Sign in to view your quotes, private enquiries, and customized itinerary history.</p>

        <div className="flex gap-4 my-6">
          <Link to="/login" className="gold">
            Sign In →
          </Link>
          <Link to="/register" className="pill">
            Register Account
          </Link>
        </div>

        <section className="mt-10 pt-8 border-t border-border">
          <h2 className="text-xl font-semibold mb-2">Anonymous guest browser session</h2>
          <p className="text-sm text-muted-foreground mb-4">
            If you prefer not to register, you can remember this browser for 30 days to return to saved journeys.
          </p>
          <label className="pill cursor-pointer">
            <input
              type="checkbox"
              className="mr-2"
              checked={rememberBrowser}
              onChange={async (e) => {
                const checked = e.target.checked;
                try {
                  await api("/session", {
                    method: "POST",
                    body: JSON.stringify({ remember: checked }),
                  });
                  setRememberBrowser(checked);
                } catch {
                  // Ignore
                }
              }}
            />
            Remember this browser
          </label>
        </section>
      </main>
    );
  }

  return (
    <main className="folio">
      <div className="flex items-center justify-between flex-wrap gap-4 mb-2">
        <div>
          <p className="eyebrow">Authenticated Traveller</p>
          <h1 className="mb-0">{user.full_name}</h1>
        </div>
        <button onClick={handleLogout} className="pill text-sm hover:border-black">
          Sign out
        </button>
      </div>

      <div className="flex items-center gap-3 text-sm text-muted-foreground mb-8">
        <span>{user.email}</span>
        <span>•</span>
        <span className="capitalize px-2.5 py-0.5 rounded-full text-xs font-semibold bg-saffron-wash text-ink border border-saffron/40">
          Role: {user.role}
        </span>
        {user.role !== "traveller" && (
          <Link to="/staff" className="text-xs font-semibold text-maroon underline ml-2">
            Open Staff Console ↗
          </Link>
        )}
      </div>

      {/* OVERVIEW SECTION */}
      <section className="bg-paper-deep rounded-2xl p-6 mb-10 border border-border">
        <h2 className="text-lg font-semibold mb-4">Your travel activity overview</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="bg-white p-4 rounded-xl border border-border shadow-xs">
            <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Verified Quotes</p>
            <p className="text-2xl font-bold mt-1">{overview?.total_quotes ?? 0}</p>
            <Link to="/quotes" className="text-xs font-semibold text-ink underline mt-2 inline-block">
              View all quotes →
            </Link>
          </div>
          <div className="bg-white p-4 rounded-xl border border-border shadow-xs">
            <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Private Enquiries</p>
            <p className="text-2xl font-bold mt-1">{overview?.total_enquiries ?? 0}</p>
            <span className="text-xs text-muted-foreground mt-2 block">Handled by Ceylon Specialists</span>
          </div>
          <div className="bg-white p-4 rounded-xl border border-border shadow-xs">
            <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Saved Journeys</p>
            <p className="text-2xl font-bold mt-1">{overview?.total_trips ?? overview?.trips?.length ?? 0}</p>
            <Link to="/trips" className="text-xs font-semibold text-ink underline mt-2 inline-block">
              Open notebook →
            </Link>
          </div>
        </div>

        {overview && overview.enquiries.length > 0 && (
          <div className="bg-white p-5 rounded-xl border border-border mb-6">
            <h3 className="font-semibold text-base mb-3">Recent private enquiries</h3>
            <div className="divide-y divide-border">
              {overview.enquiries.map((eq) => (
                <div key={eq.id} className="py-3 flex flex-wrap items-center justify-between gap-3 text-sm">
                  <div>
                    <p className="font-semibold text-ink">
                      {eq.tour_name || "Sri Lanka enquiry"}{" "}
                      <span className="text-xs font-mono text-muted-foreground ml-1">
                        ({eq.reference || eq.id.slice(0, 8)})
                      </span>
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {eq.human_reason || eq.reason}
                      {eq.travel_date ? ` • Date: ${eq.travel_date}` : ""}
                      {eq.adults ? ` • ${eq.adults} adults` : ""}
                      {eq.children_count ? `, ${eq.children_count} children` : ""}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Created: {eq.created.replace("T", " ").replace("Z", " UTC")}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold uppercase bg-paper-deep border border-border">
                      {eq.status}
                    </span>
                    {eq.trip_id && (
                      <Link to="/plan" search={{ id: eq.trip_id }} className="pill text-xs font-semibold">
                        Resume →
                      </Link>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {overview?.last_quote && (
          <div className="bg-white p-5 rounded-xl border border-saffron/50">
            <div className="flex justify-between items-start flex-wrap gap-2 mb-2">
              <h3 className="font-semibold text-base">{overview.last_quote.title}</h3>
              <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                overview.last_quote.current ? "bg-leaf/10 text-ink" : "bg-sun/10 text-ink"
              }`}>
                {overview.last_quote.current ? "Current verified rate" : "Rate needs rechecking"}
              </span>
            </div>
            <p className="text-sm text-muted-foreground mb-3">
              Tour date: {overview.last_quote.date} • {overview.last_quote.adults} Adults
            </p>
            <div className="flex items-baseline gap-3">
              <span className="text-xl font-bold">USD {overview.last_quote.total.toLocaleString()}</span>
              <span className="text-xs text-muted-foreground">Deposit: USD {overview.last_quote.deposit.toLocaleString()}</span>
            </div>
          </div>
        )}
      </section>

      {/* EDIT PROFILE & TRAVEL PREFERENCES */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-2">Traveller details & travel preferences</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Mira remembers these preferences so you don’t have to answer the same questions repeatedly.
        </p>

        {profileMsg && (
          <div
            role="status"
            className={`my-3 p-3 rounded-lg text-sm ${
              profileMsg.includes("successfully")
                ? "bg-leaf/10 text-ink border border-leaf/50"
                : "bg-coral/10 text-ink border border-coral/50"
            }`}
          >
            {profileMsg}
          </div>
        )}

        <form onSubmit={handleProfileUpdate} className="fields">
          <label>
            Full display name
            <input
              type="text"
              required
              value={fullName}
              disabled={profileBusy}
              onChange={(e) => setFullName(e.target.value)}
            />
          </label>

          <label>
            Permitted contact phone number
            <input
              type="tel"
              value={phone}
              disabled={profileBusy}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+94 77 123 4567"
            />
          </label>

          <label>
            Dietary preferences (e.g. Vegetarian, Halal, Vegan, Gluten-free)
            <input
              type="text"
              value={dietary}
              disabled={profileBusy}
              onChange={(e) => setDietary(e.target.value)}
              placeholder="e.g. Vegetarian, Ceylon spices preferred"
            />
          </label>

          <label>
            Preferred travel pace
            <select
              value={travelPace}
              disabled={profileBusy}
              onChange={(e) => setTravelPace(e.target.value)}
            >
              <option value="">Select travel style…</option>
              <option value="relaxed">Relaxed (Boutique tea estates, leisurely drives)</option>
              <option value="balanced">Balanced (Culture, scenic train rides, beaches)</option>
              <option value="active">Active (Hikes, wildlife safaris, water sports)</option>
            </select>
          </label>

          <button type="submit" disabled={profileBusy} className="gold justify-self-start mt-2">
            {profileBusy ? "Saving…" : "Save Preferences"}
          </button>
        </form>
      </section>

      {/* PASSWORD CHANGE */}
      <section className="pt-8 border-t border-border">
        <h2 className="text-xl font-semibold mb-2">Change account password</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Updating your password will revoke all other active sessions across browsers.
        </p>

        {pwdMsg && (
          <div
            role="status"
            className={`my-3 p-3 rounded-lg text-sm ${
              pwdMsg.includes("successfully")
                ? "bg-leaf/10 text-ink border border-leaf/50"
                : "bg-coral/10 text-ink border border-coral/50"
            }`}
          >
            {pwdMsg}
          </div>
        )}

        <form onSubmit={handlePasswordChange} className="fields max-w-md">
          <label>
            Current password
            <input
              type="password"
              required
              value={currPassword}
              disabled={pwdBusy}
              onChange={(e) => setCurrPassword(e.target.value)}
            />
          </label>

          <label>
            New password (min. 8 characters)
            <input
              type="password"
              required
              minLength={8}
              value={newPassword}
              disabled={pwdBusy}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </label>

          <button type="submit" disabled={pwdBusy} className="pill justify-self-start mt-2">
            {pwdBusy ? "Updating…" : "Update Password"}
          </button>
        </form>
      </section>
    </main>
  );
}

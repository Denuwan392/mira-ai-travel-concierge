import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { api, session } from "@/lib/live/service";
export const Route = createFileRoute("/sign-in")({ component: Profile });
function Profile() {
  const [remember, setRemember] = useState(false),
    [status, setStatus] = useState(""),
    [busy, setBusy] = useState(true);
  useEffect(() => {
    session()
      .then(() => api<{ remember: boolean }>("/session"))
      .then((s) => setRemember(s.remember))
      .catch(() => setStatus("Session service unavailable."))
      .finally(() => setBusy(false));
  }, []);
  return (
    <main className="folio">
      <p className="eyebrow">Private visitor session</p>
      <h1>Your notebook</h1>
      <p>
        Remember this browser for 30 days to return to saved journeys. Turn this off to use a
        session cookie.
      </p>
      <label className="pill">
        <input
          type="checkbox"
          disabled={busy}
          checked={remember}
          onChange={async (e) => {
            const value = e.target.checked;
            setBusy(true);
            try {
              await api("/session", { method: "POST", body: JSON.stringify({ remember: value }) });
              setRemember(value);
              setStatus("Preference saved.");
            } catch {
              setStatus("Could not save. Try again.");
            } finally {
              setBusy(false);
            }
          }}
        />{" "}
        Remember this browser
      </label>
      <p role="status">{status}</p>
      <Link className="gold" to="/trips">
        Open my trips →
      </Link>
    </main>
  );
}

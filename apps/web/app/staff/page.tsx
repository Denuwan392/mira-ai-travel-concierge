"use client";

import { ClipboardList, Compass, FilePenLine, LogOut, Shield } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { api } from "../../lib/api";

const statuses = ["new", "contacted", "waiting", "closed"];
type Row = { id: string; reason: string; status: string; created: string; quote: string | null; trip: string; trace: string };
type Detail = Row & { events: object[]; finance: { cost_lkr: string; total: number; deposit: number; gross_profit_pct: string } | null; notes: { actor: string; body: string; created: string }[] };
type Draft = { id: string; title: string; body: string; source: string; author: string; status: string; created: string; published?: string };
type Audit = { id: number; action: string; actor: string; target: string; created: string };

export default function Staff() {
  const [token, setToken] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const [view, setView] = useState("enquiries");
  const [filter, setFilter] = useState("");
  const [detail, setDetail] = useState<Detail>();
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [audit, setAudit] = useState<Audit[]>([]);
  const [role, setRole] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<Draft>();

  useEffect(() => {
    api<{ role: string }>("/staff/me")
      .then((identity) => {
        if (["staff", "editor", "approver", "admin"].includes(identity.role)) {
          setRole(identity.role);
          setToken("session");
          api<Row[]>("/staff/enquiries").then(setRows).catch(() => {});
        }
      })
      .catch(() => {});
  }, []);

  const auth = (key = token): Record<string, string> =>
    key && key !== "session" ? { Authorization: `Bearer ${key}` } : {};
  const call = <T,>(path: string, options: RequestInit = {}) =>
    api<T>(`/staff${path}`, {
      ...options,
      headers: { ...auth(), ...(options.headers as Record<string, string> | undefined) },
    });
  const error = (e: unknown) => setMessage(e instanceof Error ? e.message : "This action couldn’t complete.");

  async function login(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setMessage("");
    const key = String(new FormData(e.currentTarget).get("token")).trim();
    try {
      const [next, identity] = await Promise.all([
        api<Row[]>("/staff/enquiries", { headers: auth(key) }),
        api<{ role: string }>("/staff/me", { headers: auth(key) }),
      ]);
      setRows(next); setToken(key); setRole(identity.role);
    } catch (e) { error(e); }
    finally { setBusy(false); }
  }

  async function choose(next: string) {
    setMessage("");
    setView(next);
    setPreview(undefined);
    try {
      if (next === "content") setDrafts(await call<Draft[]>("/drafts"));
      if (next === "audit") setAudit(await call<Audit[]>("/audit"));
    } catch (e) { error(e); }
  }

  async function open(id: string) {
    setMessage("");
    try { setDetail(await call<Detail>(`/enquiries/${id}`)); }
    catch (e) { error(e); }
  }

  async function follow(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!detail) return;
    const data = new FormData(e.currentTarget);
    setBusy(true);
    try {
      await call(`/enquiries/${detail.id}`, { method: "PATCH", body: JSON.stringify({ status: data.get("status"), note: data.get("note") }) });
      setRows(await call<Row[]>("/enquiries"));
      await open(detail.id);
      setMessage("Follow-up saved.");
    } catch (e) { error(e); }
    finally { setBusy(false); }
  }

  async function generate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const command = new FormData(form).get("command");
    setBusy(true);
    setMessage("");
    try {
      const result = await call<{id: string; mode: string}>("/drafts", { method: "POST", body: JSON.stringify({ command }) });
      const refreshed = await call<Draft[]>("/drafts");
      setDrafts(refreshed); setPreview(refreshed.find(item => item.id === result.id));
      setMessage(`Draft created · ${result.mode}`);
      form.reset();
    } catch (e) { error(e); }
    finally { setBusy(false); }
  }

  async function publish() {
    if (!preview) return;
    setBusy(true);
    setMessage("");
    try {
      await call(`/drafts/${preview.id}/publish`, { method: "POST" });
      const refreshed = await call<Draft[]>("/drafts");
      setDrafts(refreshed); setPreview(refreshed.find(item => item.id === preview.id));
      setMessage("Published. The journey is now available to Mira.");
    } catch (e) { error(e); }
    finally { setBusy(false); }
  }

  return <main className="frame workspace staff-page">
    <div className="workspace-heading"><span className="eyebrow"><Shield size={16} /> CEYLON COMPASS OPERATIONS</span><h1>Staff console</h1></div>
    {!token ? <form className="panel staff-login" onSubmit={login}>
      <div className="avatar"><Compass size={25} /></div><h2>Sign in to staff</h2>
      <label>Staff access token<input name="token" type="password" autoComplete="off" minLength={24} required /></label>
      <button className="button primary" disabled={busy}>Sign in</button>
      {message && <p role="alert">{message}</p>}
    </form> : <div className="staff-layout">
      <aside className="panel staff-nav">
        <span className="eyebrow">ROLE · {role}</span>
        <button className="text-button" aria-current={view === "enquiries" ? "page" : undefined} onClick={() => void choose("enquiries")}><ClipboardList size={17} /> Enquiries</button>
        {role !== "staff" && <button className="text-button" aria-current={view === "content" ? "page" : undefined} onClick={() => void choose("content")}><FilePenLine size={17} /> Content studio</button>}
        <button className="text-button" aria-current={view === "audit" ? "page" : undefined} onClick={() => void choose("audit")}><Shield size={17} /> Audit log</button>
        <button className="text-button" onClick={() => { setToken(""); setRows([]); setDetail(undefined); setPreview(undefined); setDrafts([]); setAudit([]); setMessage(""); setView("enquiries"); }}><LogOut size={17} /> Sign out</button>
      </aside>
      <div className="staff-content">
        {message && <p className="panel" role="status">{message}</p>}
        {view === "enquiries" && <>
          <div className="metric-grid"><div className="panel"><strong>{rows.length}</strong>Recent enquiries</div><div className="panel"><strong>{rows.filter(r => r.status === "new").length}</strong>New</div><div className="panel"><strong>{rows.filter(r => !r.quote).length}</strong>Specialist flags</div></div>
          <section className="panel">
            <div className="table-heading"><h2>Enquiries</h2><label>Status<select value={filter} onChange={e => setFilter(e.target.value)}><option value="">All statuses</option>{statuses.map(s => <option key={s}>{s}</option>)}</select></label></div>
            {rows.filter(r => !filter || r.status === filter).length ? <div className="table-scroll"><table><thead><tr><th>Reference</th><th>Type</th><th>Status</th><th>Created (UTC)</th></tr></thead><tbody>
              {rows.filter(r => !filter || r.status === filter).map(r => <tr key={r.id}><td><button className="text-button" onClick={() => void open(r.id)}>{r.id.slice(0, 8)}</button></td><td>{r.quote ? "Verified quote" : "Specialist review"}</td><td>{r.status}</td><td>{r.created}</td></tr>)}
            </tbody></table></div> : <p>No enquiries match this view.</p>}
          </section>
          {detail && <section className="panel enquiry-detail">
            <div className="table-heading"><h2>Enquiry {detail.id.slice(0, 8)}</h2><button className="button outline" onClick={() => setDetail(undefined)}>Close</button></div>
            <p>{detail.reason.replaceAll("_", " ")}</p><pre>{JSON.stringify(JSON.parse(detail.trip), null, 2)}</pre>
            <details><summary>Trace {detail.trace.slice(0, 8)}</summary><pre>{JSON.stringify(detail.events, null, 2)}</pre></details>
            {detail.finance && <details><summary>Internal finance</summary><dl className="finance-summary">
              <div><dt>Cost</dt><dd>LKR {Number(detail.finance.cost_lkr).toLocaleString("en-US")}</dd></div>
              <div><dt>Selling price</dt><dd>USD {detail.finance.total.toLocaleString("en-US")}</dd></div>
              <div><dt>Deposit</dt><dd>USD {detail.finance.deposit.toLocaleString("en-US")}</dd></div>
              <div><dt>Gross profit</dt><dd>{Number(detail.finance.gross_profit_pct).toFixed(2)}%</dd></div>
            </dl><details><summary>Workbook calculation</summary><pre>{JSON.stringify(detail.finance, null, 2)}</pre></details></details>}
            <ul>{detail.notes.map((n, i) => <li key={i}>{n.actor} · {n.body}</li>)}</ul>
            <form onSubmit={follow} key={`${detail.id}-${detail.notes.length}-${detail.status}`}>
              <label>New status<select name="status" defaultValue={detail.status}>{statuses.map(s => <option key={s}>{s}</option>)}</select></label>
              <label>Staff note<textarea name="note" maxLength={500} placeholder="Trip details only" /></label>
              <button className="button primary" disabled={busy}>Save follow-up</button>
            </form>
          </section>}
        </>}
        {view === "content" && <>
          <form className="panel staff-form" onSubmit={generate}><h2>Content studio</h2>
            <label>Draft request<textarea name="command" placeholder="Create a Hill Country journey concept using published Ella material" minLength={5} maxLength={300} required /></label>
            <button className="button primary" disabled={busy}>Create draft</button>
          </form>
          <section className="panel"><h2>Drafts and published journeys</h2>
            {drafts.length ? drafts.map(d => <div className="draft-row" key={d.id}><button className="text-button" onClick={() => setPreview(d)}>{d.title}</button><span>{d.status}</span></div>) : <p>No drafts yet.</p>}
          </section>
          {preview && <section className="panel excerpt">
            <h2>{preview.title}</h2><p className="muted">{preview.status} · {preview.author} · Source {preview.source}</p><p>{preview.body}</p>
            {preview.status === "draft" && (role === "approver" ? <button className="button primary" disabled={busy} onClick={() => void publish()}>Approve and publish</button> : <p>Only an Approver can publish this draft.</p>)}
          </section>}
        </>}
        {view === "audit" && <section className="panel"><h2>Audit log</h2>{audit.length ? audit.map(e => <div className="draft-row" key={e.id}><span>{e.action} · {e.actor}</span><span>{e.created} UTC</span></div>) : <p>No recorded actions.</p>}</section>}
      </div>
    </div>}
  </main>;
}

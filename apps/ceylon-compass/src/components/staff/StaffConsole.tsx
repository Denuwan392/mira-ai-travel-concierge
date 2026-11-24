import { useCallback, useEffect, useRef, useState, type CSSProperties, type FormEvent } from "react";
import { api } from "@/lib/live/service";
import { Search, Shield, X, Check, AlertCircle, Clock, FileText, Users, Activity } from "lucide-react";

type DashboardOverview = {
  total_enquiries: number;
  open_enquiries: number;
  pending_followups: number;
  contactable_enquiries: number;
  unassigned_enquiries: number;
  missing_rate_enquiries: number;
  quotes_requiring_confirmation: number;
  pending_content_approvals: number;
  recent_activity: { id: number; actor: string; action: string; target: string; created: string }[];
};

type EnquiryRow = {
  id: string;
  reference?: string;
  reason: string;
  human_reason?: string;
  enquiry_category?: string;
  status: string;
  created: string;
  updated_at?: string;
  last_activity_at?: string;
  follow_up_date?: string | null;
  quote: string | null;
  trip: string;
  trace: string;
  assigned_to?: string | null;
  assigned_name?: string | null;
  tour_id?: string | null;
  tour_name?: string;
  travel_date?: string | null;
  adults?: number | null;
  children_count?: number;
  child_ages?: number[];
  quoted_total_usd?: number | null;
  quoted_deposit_usd?: number | null;
  mock_booking_status?: string | null;
  mock_booking_reference?: string | null;
  special_requests?: string;
  is_contactable?: boolean;
  traveller_type?: string;
  traveller_name?: string;
  traveller_email?: string;
  traveller_phone?: string;
};

type QuoteRevision = {
  id: string;
  tour_id: string | null;
  date: string | null;
  adults: number | null;
  ages: number[];
  total: number | null;
  deposit: number | null;
  cost_lkr: string | null;
  gross_profit_pct: string | null;
  created: string | null;
  is_latest: boolean;
};

type EnquiryDetail = EnquiryRow & {
  events: { stage: string; [key: string]: unknown }[];
  finance: { cost_lkr?: string; total?: number; deposit?: number; gross_profit_pct?: string } | null;
  notes: { id?: number; actor: string; body: string; created: string }[];
  quote_history?: QuoteRevision[];
};

type DraftRow = {
  id: string;
  title: string;
  body: string;
  source: string;
  author: string;
  status: string;
  created: string;
  published?: string | null;
  reviewer?: string;
  review_notes?: string;
  reviewed_at?: string | null;
};

type UserRow = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  status: string;
  phone: string;
  created_at: string;
};

type AssignableStaff = {
  id: string;
  full_name: string;
  email: string;
  role: string;
};

type AuditRow = {
  id: number;
  action: string;
  actor: string;
  target: string;
  created: string;
};

type EvalReport = {
  as_of: string;
  generated_at: string;
  summary: {
    overall_pass_rate_pct: number;
    passed_cases: number;
    total_cases: number;
    employer_cases: number;
    authored_cases: number;
    multi_turn_conversations: number;
    validated_ui_turns: number;
    total_attempted_turns: number;
  };
  categories: Record<string, { pass: number; total: number }>;
  results?: { id: string; pass: boolean; failure?: string; traces?: { id: string; stages: unknown[] }[] }[];
};

type PricingPreviewResult = {
  preview_only: boolean;
  outcome: "PRICE_VERIFIED" | "PRICE_UNAVAILABLE" | "PRICE_VALIDATION_ERROR" | "PRICING_SERVICE_ERROR";
  rate_digest: string | null;
  evaluated_config: {
    tour_id: string;
    tour_title: string;
    date: string;
    adults: number;
    child_ages: number[];
    infants: number;
    as_of: string;
  };
  currency: string;
  total_usd: number | null;
  deposit_usd: number | null;
  balance_usd: number | null;
  snapshot: string | null;
  reason_code: string | null;
  reason: string | null;
  finance: {
    cost_lkr: string;
    gross_profit_pct: string;
    breakdown: Record<string, string>;
  } | null;
};

export interface StaffConsoleProps {
  onAuthChange?: () => void | Promise<void>;
  defaultTab?: "enquiries" | "overview" | "content" | "preview" | "users" | "audit";
}

function formatTs(iso?: string | null) {
  if (!iso) return "—";
  try {
    let s = String(iso).trim();
    if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/.test(s)) {
      s = s.replace(" ", "T");
    }
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$/.test(s)) {
      s += "Z";
    }
    const d = new Date(s);
    if (Number.isNaN(d.getTime())) return String(iso);
    return d.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return String(iso);
  }
}

function statusBadgeStyle(st: string) {
  switch (st) {
    case "new":
      return "bg-[#F26B1D]/10 text-[#F26B1D] border-[#F26B1D]/30";
    case "in_review":
      return "bg-[#F5B700]/15 text-[#855800] border-[#F5B700]/40";
    case "contacted":
    case "quoted":
      return "bg-[#3A8DDE]/15 text-[#175C9E] border-[#3A8DDE]/30";
    case "waiting":
    case "waiting_customer":
      return "bg-purple-100 text-purple-800 border-purple-200";
    case "booked":
      return "bg-[#4CA64C]/15 text-[#276327] border-[#4CA64C]/30";
    case "closed":
    case "closed_lost":
    case "unqualified":
      return "bg-gray-100 text-[#5F5F5F] border-gray-200";
    default:
      return "bg-[#14837B]/10 text-[#14837B] border-[#14837B]/30";
  }
}

export function StaffConsole({ onAuthChange, defaultTab = "overview" }: StaffConsoleProps) {
  const [currentUser, setCurrentUser] = useState<{ role: string; email?: string; full_name?: string } | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [authError, setAuthError] = useState("");
  const [activeTab, setActiveTab] = useState<"enquiries" | "overview" | "content" | "preview" | "users" | "audit">(defaultTab);

  // Login form state
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginBusy, setLoginBusy] = useState(false);

  // Overview & Evaluation state
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [evalReport, setEvalReport] = useState<EvalReport | null>(null);

  // Enquiries state
  const [enquiries, setEnquiries] = useState<EnquiryRow[]>([]);
  const [totalEnquiries, setTotalEnquiries] = useState(0);
  const [enquiryFilter, setEnquiryFilter] = useState("");
  const [enquirySearch, setEnquirySearch] = useState("");
  const [enquiryAssignedFilter, setEnquiryAssignedFilter] = useState("");
  const [enquiryContactableFilter, setEnquiryContactableFilter] = useState("");
  const [enquirySort, setEnquirySort] = useState("newest");
  const [page, setPage] = useState(0);
  const pageSize = 25;

  const [selectedEnquiry, setSelectedEnquiry] = useState<EnquiryDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [assignableStaff, setAssignableStaff] = useState<AssignableStaff[]>([]);
  const [noteInput, setNoteInput] = useState("");
  const [statusInput, setStatusInput] = useState("new");
  const [assignedStaffInput, setAssignedStaffInput] = useState("");
  const [followUpDateInput, setFollowUpDateInput] = useState("");
  const [enquiryActionMsg, setEnquiryActionMsg] = useState<{ type: string; text: string }>({ type: "", text: "" });
  const [enquiryBusy, setEnquiryBusy] = useState(false);
  const [showTrace, setShowTrace] = useState(false);

  // Content review state
  const [drafts, setDrafts] = useState<DraftRow[]>([]);
  const [draftPrompt, setDraftPrompt] = useState("");
  const [selectedDraft, setSelectedDraft] = useState<DraftRow | null>(null);
  const [reviewNotes, setReviewNotes] = useState("");
  const [draftMsg, setDraftMsg] = useState("");
  const [draftBusy, setDraftBusy] = useState(false);

  // User admin state
  const [users, setUsers] = useState<UserRow[]>([]);
  const [userSearch, setUserSearch] = useState("");
  const [userMsg, setUserMsg] = useState("");
  const [userBusy, setUserBusy] = useState(false);

  // Audit state
  const [auditRows, setAuditRows] = useState<AuditRow[]>([]);

  // Read-only Rate Preview state
  const [previewTours, setPreviewTours] = useState<{ id: string; title: string; duration?: string }[]>([]);
  const [previewTourId, setPreviewTourId] = useState("T01");
  const [previewDate, setPreviewDate] = useState("2027-01-10");
  const [previewAdults, setPreviewAdults] = useState(2);
  const [previewChildAgesText, setPreviewChildAgesText] = useState("");
  const [previewInfants, setPreviewInfants] = useState(0);
  const [previewBusy, setPreviewBusy] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [previewResult, setPreviewResult] = useState<PricingPreviewResult | null>(null);

  const [workspaceHeight, setWorkspaceHeight] = useState<string | null>(null);
  const workspaceRef = useRef<HTMLDivElement | null>(null);
  const detailRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (activeTab !== "enquiries") return;
    function measure() {
      if (!workspaceRef.current || window.innerWidth < 1024) {
        setWorkspaceHeight(null);
        return;
      }
      const rect = workspaceRef.current.getBoundingClientRect();
      const available = Math.max(360, Math.floor(window.innerHeight - Math.max(0, rect.top) - 24));
      setWorkspaceHeight(`${available}px`);
    }
    const raf = requestAnimationFrame(measure);
    window.addEventListener("resize", measure);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", measure);
    };
  }, [activeTab, enquiries.length, selectedEnquiry?.id]);

  const loadEnquiries = useCallback(
    async (opts: {
      status?: string;
      search?: string;
      assigned_to?: string;
      contactable?: string;
      sort?: string;
      page?: number;
    } = {}) => {
      const q = new URLSearchParams();
      const st = opts.status !== undefined ? opts.status : enquiryFilter;
      const sr = opts.search !== undefined ? opts.search : enquirySearch;
      const asg = opts.assigned_to !== undefined ? opts.assigned_to : enquiryAssignedFilter;
      const ct = opts.contactable !== undefined ? opts.contactable : enquiryContactableFilter;
      const so = opts.sort !== undefined ? opts.sort : enquirySort;
      const pg = opts.page !== undefined ? opts.page : page;

      if (st) q.set("status", st);
      if (sr) q.set("search", sr);
      if (asg) q.set("assigned_to", asg);
      if (ct) q.set("contactable", ct);
      if (so) q.set("sort", so);
      q.set("limit", String(pageSize));
      q.set("offset", String(pg * pageSize));

      const res = await fetch("/api/staff/enquiries?" + q.toString(), { cache: "no-store" });
      if (res.ok) {
        const totalHdr = res.headers.get("X-Total-Count");
        const rows: EnquiryRow[] = await res.json();
        setEnquiries(rows);
        setTotalEnquiries(totalHdr ? Number(totalHdr) : rows.length);
      }
    },
    [enquiryFilter, enquirySearch, enquiryAssignedFilter, enquiryContactableFilter, enquirySort, page],
  );

  const loadDashboardData = useCallback(async () => {
    try {
      const [ov, staffList, ev] = await Promise.all([
        api<DashboardOverview>("/staff/dashboard/overview").catch(() => null),
        api<AssignableStaff[]>("/staff/users/assignable").catch(() => []),
        api<EvalReport>("/staff/evaluation").catch(() => null),
      ]);
      if (ov) setOverview(ov);
      if (staffList) setAssignableStaff(staffList);
      if (ev) setEvalReport(ev);
      await loadEnquiries();
    } catch {
      // ignore transient errors
    }
  }, [loadEnquiries]);

  useEffect(() => {
    api<{ role: string; email?: string; full_name?: string }>("/staff/me")
      .then((res) => {
        if (["staff", "editor", "approver", "admin"].includes(res.role)) {
          setCurrentUser(res);
          loadDashboardData();
        }
      })
      .catch(() => {})
      .finally(() => setAuthChecked(true));
  }, [loadDashboardData]);

  async function loadDrafts() {
    try {
      const list = await api<DraftRow[]>("/staff/drafts");
      setDrafts(list);
      if (selectedDraft) {
        const updated = list.find((d) => d.id === selectedDraft.id);
        if (updated) setSelectedDraft(updated);
      }
    } catch (err) {
      setDraftMsg(err instanceof Error ? err.message : "Failed to load drafts.");
    }
  }

  async function loadUsers() {
    try {
      const params = new URLSearchParams();
      if (userSearch) params.set("search", userSearch);
      const list = await api<UserRow[]>("/admin/users?" + params.toString());
      setUsers(list);
    } catch (err) {
      setUserMsg(err instanceof Error ? err.message : "Failed to load users.");
    }
  }

  async function loadAudit() {
    try {
      const endpoint = currentUser?.role === "admin" ? "/admin/audit" : "/staff/audit";
      const rows = await api<AuditRow[]>(endpoint);
      setAuditRows(rows);
    } catch {
      // ignore
    }
  }

  async function loadPreviewTours() {
    if (previewTours.length > 0) return;
    try {
      const list = await api<{ id: string; title: string; duration?: string }[]>("/tours");
      if (Array.isArray(list) && list.length > 0) {
        setPreviewTours(list);
      }
    } catch {
      // ignore; user can still use default tour ID
    }
  }

  async function handleRunPreview(e: FormEvent) {
    e.preventDefault();
    setPreviewError("");
    setPreviewBusy(true);
    try {
      const parsedAges = previewChildAgesText
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((s) => Number(s));
      if (parsedAges.some((n) => !Number.isInteger(n) || n < 0 || n > 120)) {
        setPreviewError("Child ages must be whole numbers between 0 and 120, separated by commas.");
        setPreviewBusy(false);
        return;
      }
      const res = await api<PricingPreviewResult>("/staff/pricing/preview", {
        method: "POST",
        body: JSON.stringify({
          tour_id: previewTourId,
          date: previewDate,
          adults: Number(previewAdults),
          child_ages: parsedAges,
          infants: Number(previewInfants),
        }),
      });
      setPreviewResult(res);
    } catch (err) {
      setPreviewResult(null);
      setPreviewError(err instanceof Error ? err.message : "Failed to run pricing preview.");
    } finally {
      setPreviewBusy(false);
    }
  }

  function handleTabChange(tab: "overview" | "enquiries" | "content" | "preview" | "users" | "audit") {
    setActiveTab(tab);
    if (tab === "overview") loadDashboardData();
    if (tab === "enquiries") loadEnquiries();
    if (tab === "content") loadDrafts();
    if (tab === "preview") loadPreviewTours();
    if (tab === "users") loadUsers();
    if (tab === "audit") loadAudit();
  }

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setAuthError("");
    setLoginBusy(true);
    try {
      await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: loginEmail, password: loginPassword, remember: true }),
      });
      const identity = await api<{ role: string; email?: string; full_name?: string }>("/staff/me");
      if (!["staff", "editor", "approver", "admin"].includes(identity.role)) {
        setAuthError("Your account does not have staff console privileges.");
        setCurrentUser(null);
        return;
      }
      setCurrentUser(identity);
      await onAuthChange?.();
      await loadDashboardData();
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "Invalid staff credentials.");
    } finally {
      setLoginBusy(false);
    }
  }

  async function handleLogout() {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      // ignore
    } finally {
      setCurrentUser(null);
      setSelectedEnquiry(null);
      await onAuthChange?.();
    }
  }

  async function openEnquiryDetail(id: string) {
    setDetailLoading(true);
    setEnquiryActionMsg({ type: "", text: "" });
    setShowTrace(false);
    try {
      const detail = await api<EnquiryDetail>(`/staff/enquiries/${encodeURIComponent(id)}`);
      setSelectedEnquiry(detail);
      setStatusInput(detail.status || "new");
      setAssignedStaffInput(detail.assigned_to || "");
      setFollowUpDateInput(detail.follow_up_date || "");
      setNoteInput("");
      if (detailRef.current) {
        detailRef.current.scrollTop = 0;
      }
    } catch (err) {
      setEnquiryActionMsg({ type: "error", text: err instanceof Error ? err.message : "Failed to load enquiry." });
    } finally {
      setDetailLoading(false);
    }
  }

  async function handleFollowUp(e: FormEvent) {
    e.preventDefault();
    if (!selectedEnquiry) return;
    setEnquiryBusy(true);
    setEnquiryActionMsg({ type: "", text: "" });
    try {
      await api(`/staff/enquiries/${encodeURIComponent(selectedEnquiry.id)}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: statusInput,
          note: noteInput,
          assigned_to: assignedStaffInput || null,
          follow_up_date: followUpDateInput || "",
        }),
      });
      setNoteInput("");
      await Promise.all([
        openEnquiryDetail(selectedEnquiry.id),
        loadEnquiries(),
        api<DashboardOverview>("/staff/dashboard/overview").then((ov) => ov && setOverview(ov)).catch(() => {}),
      ]);
      setEnquiryActionMsg({ type: "success", text: "Follow-up saved." });
    } catch (err) {
      setEnquiryActionMsg({ type: "error", text: err instanceof Error ? err.message : "Failed to save update." });
    } finally {
      setEnquiryBusy(false);
    }
  }

  async function handleGenerateDraft(e: FormEvent) {
    e.preventDefault();
    if (!draftPrompt.trim()) return;
    setDraftBusy(true);
    setDraftMsg("");
    try {
      const res = await api<{ id: string; mode: string }>("/staff/drafts", {
        method: "POST",
        body: JSON.stringify({ command: draftPrompt.trim() }),
      });
      setDraftPrompt("");
      setDraftMsg(`Draft created (${res.mode}): ${res.id}`);
      await Promise.all([
        loadDrafts(),
        api<DashboardOverview>("/staff/dashboard/overview").then((ov) => ov && setOverview(ov)).catch(() => {}),
      ]);
    } catch (err) {
      setDraftMsg(err instanceof Error ? err.message : "Failed to create draft.");
    } finally {
      setDraftBusy(false);
    }
  }

  async function handleReviewDraft(action: "approve" | "request_revision" | "reject") {
    if (!selectedDraft) return;
    setDraftBusy(true);
    setDraftMsg("");
    try {
      const res = await api<{ status: string; id: string }>(`/staff/drafts/${encodeURIComponent(selectedDraft.id)}/review`, {
        method: "POST",
        body: JSON.stringify({ action, notes: reviewNotes }),
      });
      setReviewNotes("");
      setDraftMsg(`Draft status updated to '${res.status}'.`);
      await Promise.all([
        loadDrafts(),
        api<DashboardOverview>("/staff/dashboard/overview").then((ov) => ov && setOverview(ov)).catch(() => {}),
      ]);
    } catch (err) {
      setDraftMsg(err instanceof Error ? err.message : "Review failed.");
    } finally {
      setDraftBusy(false);
    }
  }

  async function handlePublishDraft() {
    if (!selectedDraft) return;
    setDraftBusy(true);
    setDraftMsg("");
    try {
      await api(`/staff/drafts/${encodeURIComponent(selectedDraft.id)}/publish`, { method: "POST" });
      setDraftMsg("Draft published! Mira can now retrieve this journey.");
      await Promise.all([
        loadDrafts(),
        api<DashboardOverview>("/staff/dashboard/overview").then((ov) => ov && setOverview(ov)).catch(() => {}),
      ]);
    } catch (err) {
      setDraftMsg(err instanceof Error ? err.message : "Publish failed.");
    } finally {
      setDraftBusy(false);
    }
  }

  async function handleUpdateUser(uid: string, patch: { role?: string; status?: string }) {
    setUserBusy(true);
    setUserMsg("");
    try {
      await api(`/admin/users/${encodeURIComponent(uid)}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      });
      setUserMsg("User account updated successfully.");
      await Promise.all([loadUsers(), api<AssignableStaff[]>("/staff/users/assignable").then(setAssignableStaff).catch(() => {})]);
    } catch (err) {
      setUserMsg(err instanceof Error ? err.message : "Failed to update user.");
    } finally {
      setUserBusy(false);
    }
  }

  if (!authChecked) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-20 text-center text-sm text-[#5F5F5F]">
        Verifying staff session...
      </div>
    );
  }

  if (!currentUser) {
    return (
      <div className="max-w-md mx-auto px-4 sm:px-6 py-16">
        <div className="bg-white rounded-[12px] border border-[#E6E6E6] shadow-sm p-8">
          <div className="text-center mb-6">
            <div className="w-12 h-12 rounded-full bg-[#111111]/5 flex items-center justify-center mx-auto mb-3">
              <Shield className="w-6 h-6 text-[#111111]" />
            </div>
            <p className="text-xs font-semibold uppercase tracking-wider text-[#14837B]">Staff Operations</p>
            <h1 className="text-xl font-bold text-[#111111] mt-1">Staff Portal</h1>
            <p className="text-xs text-[#5F5F5F] mt-1">
              Sign in with authorized Staff, Approver, or Administrator credentials.
            </p>
          </div>
          {authError && (
            <div role="alert" className="mb-4 p-3 rounded-[8px] bg-[#E5533D]/10 border border-[#E5533D]/40 text-xs text-[#111111]">
              {authError}
            </div>
          )}
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label htmlFor="staff-email" className="text-xs font-semibold text-[#111111] block mb-1.5">
                Staff Email
              </label>
              <input
                id="staff-email"
                type="email"
                required
                value={loginEmail}
                disabled={loginBusy}
                onChange={(e) => setLoginEmail(e.target.value)}
                placeholder="staff@ceyloncompass.com"
                className="w-full px-3 py-2.5 border border-[#E6E6E6] rounded-[8px] text-sm focus:outline-none focus:border-[#F26B1D]"
              />
            </div>
            <div>
              <label htmlFor="staff-password" className="text-xs font-semibold text-[#111111] block mb-1.5">
                Password
              </label>
              <input
                id="staff-password"
                type="password"
                required
                value={loginPassword}
                disabled={loginBusy}
                onChange={(e) => setLoginPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3 py-2.5 border border-[#E6E6E6] rounded-[8px] text-sm focus:outline-none focus:border-[#F26B1D]"
              />
            </div>
            <button
              type="submit"
              disabled={loginBusy}
              className="w-full py-2.5 px-5 rounded-[999px] bg-[#F26B1D] text-white font-semibold text-sm hover:bg-[#d95a12] transition-colors cursor-pointer disabled:opacity-60"
            >
              {loginBusy ? "Signing in..." : "Sign In to Staff Console"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(totalEnquiries / pageSize));
  const failedCases = evalReport?.results?.filter((r) => !r.pass) || [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-[#14837B]">Operations & Governance</p>
          <h1 className="text-2xl font-bold text-[#111111] mt-0.5">Staff & Admin Console</h1>
          <p className="text-xs text-[#5F5F5F] mt-1">
            Signed in as <strong className="text-[#111111]">{currentUser.full_name || currentUser.email || currentUser.role}</strong>{" "}
            (<span className="uppercase font-semibold">{currentUser.role}</span>)
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <a
            href="/api/staff/evaluation"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center px-4 py-2 text-xs font-semibold border border-[#E6E6E6] bg-white rounded-[999px] text-[#111111] hover:border-[#111111] transition-colors"
          >
            View evaluation results
          </a>
          <button
            type="button"
            onClick={handleLogout}
            className="inline-flex items-center px-4 py-2 text-xs font-semibold border border-[#E6E6E6] bg-white rounded-[999px] text-[#5F5F5F] hover:text-[#111111] cursor-pointer"
          >
            Sign out
          </button>
        </div>
      </div>

      {/* Authoritative Aggregate Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          {
            label: "Open enquiries",
            value: overview?.open_enquiries ?? 0,
            sub: `${overview?.total_enquiries ?? 0} total recorded`,
            accent: "text-[#F26B1D]",
          },
          {
            label: "Contactable leads",
            value: overview?.contactable_enquiries ?? 0,
            sub: "With customer email/account",
            accent: "text-[#14837B]",
          },
          {
            label: "Pending follow-ups",
            value: overview?.pending_followups ?? 0,
            sub: "New, in review, or waiting",
            accent: "text-[#F5B700]",
          },
          {
            label: "Needs pricing",
            value: overview?.missing_rate_enquiries ?? 0,
            sub: `${overview?.unassigned_enquiries ?? 0} unassigned`,
            accent: "text-[#3A8DDE]",
          },
          {
            label: "Pending approvals",
            value: overview?.pending_content_approvals ?? 0,
            sub: "Drafts awaiting Approver",
            accent: "text-[#4CA64C]",
          },
        ].map((stat) => (
          <div key={stat.label} className="bg-white rounded-[12px] border border-[#E6E6E6] p-4 shadow-xs">
            <p className="text-xs text-[#5F5F5F] mb-1">{stat.label}</p>
            <p className={`text-2xl font-bold ${stat.accent}`}>{stat.value}</p>
            <p className="text-[11px] text-[#5F5F5F] mt-1">{stat.sub}</p>
          </div>
        ))}
      </div>

      {/* Navigation Tabs */}
      <nav aria-label="Staff sections" className="flex flex-wrap gap-2 border-b border-[#E6E6E6] pb-3">
        {[
          { id: "overview" as const, label: "Overview" },
          { id: "enquiries" as const, label: "Enquiries" },
          { id: "content" as const, label: "Content Review" },
          { id: "preview" as const, label: "Rate Preview" },
          ...(currentUser.role === "admin" ? [{ id: "users" as const, label: "User Administration" }] : []),
          { id: "audit" as const, label: "Audit History" },
        ].map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => handleTabChange(t.id)}
            className={`px-4 py-2 text-xs font-semibold rounded-[999px] cursor-pointer transition-colors ${
              activeTab === t.id
                ? "bg-[#111111] text-white"
                : "bg-white text-[#5F5F5F] border border-[#E6E6E6] hover:text-[#111111]"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* OVERVIEW TAB */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Visual Evaluation Dashboard */}
            <div className="bg-white rounded-[12px] border border-[#E6E6E6] p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-bold text-sm text-[#111111]">Automated Evaluation Suite</h2>
                {evalReport && (
                  <span className="px-2.5 py-0.5 rounded-[999px] text-xs font-bold bg-[#4CA64C]/15 text-[#276327]">
                    {evalReport.summary.passed_cases}/{evalReport.summary.total_cases} Passed ({evalReport.summary.overall_pass_rate_pct}%)
                  </span>
                )}
              </div>
              {evalReport ? (
                <>
                  <p className="text-xs text-[#5F5F5F]">
                    Clock: <strong>{evalReport.as_of}</strong> • Multi-turn: <strong>{evalReport.summary.multi_turn_conversations}</strong> • Validated UI turns:{" "}
                    <strong>{evalReport.summary.validated_ui_turns}/{evalReport.summary.total_attempted_turns}</strong>
                  </p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-[#E6E6E6] text-[#5F5F5F]">
                          <th className="text-left py-1.5">Requirement</th>
                          <th className="text-right py-1.5">Passed</th>
                          <th className="text-right py-1.5">Total</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#E6E6E6]/60">
                        {Object.entries(evalReport.categories).map(([cat, counts]) => (
                          <tr key={cat}>
                            <td className="py-1.5 capitalize font-medium text-[#111111]">{cat.replace("_", " ")}</td>
                            <td className="py-1.5 text-right">{counts.pass}</td>
                            <td className="py-1.5 text-right">{counts.total}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {failedCases.length > 0 && (
                    <div className="p-3 rounded-[8px] bg-[#F5B700]/10 border border-[#F5B700]/40 text-xs space-y-1">
                      <p className="font-semibold text-[#111111]">Known Evaluation Discrepancies ({failedCases.length}):</p>
                      {failedCases.map((fc) => (
                        <div key={fc.id} className="text-[#5F5F5F]">
                          <strong className="text-[#111111]">{fc.id}:</strong> {fc.failure}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <p className="text-xs text-[#5F5F5F]">Run <code>make eval</code> to generate an evaluation report.</p>
              )}
            </div>

            {/* Recent Activity */}
            <div className="bg-white rounded-[12px] border border-[#E6E6E6] p-6 space-y-4">
              <h2 className="font-bold text-sm text-[#111111]">Recent Staff Audit Activity</h2>
              {overview?.recent_activity?.length ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-[#E6E6E6] text-[#5F5F5F]">
                        <th className="text-left py-2">Time</th>
                        <th className="text-left py-2">Actor</th>
                        <th className="text-left py-2">Action</th>
                        <th className="text-left py-2">Target</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E6E6E6]/60">
                      {overview.recent_activity.map((a) => (
                        <tr key={a.id}>
                          <td className="py-2 text-[#5F5F5F] whitespace-nowrap">{formatTs(a.created)}</td>
                          <td className="py-2 font-medium text-[#111111]">{a.actor}</td>
                          <td className="py-2">
                            <span className="px-2 py-0.5 rounded-[999px] bg-gray-100 text-[11px] font-medium">{a.action}</span>
                          </td>
                          <td className="py-2 font-mono text-[11px] text-[#5F5F5F]">{a.target.slice(0, 14)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-xs text-[#5F5F5F]">No recent privileged audit events.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ENQUIRIES TAB */}
      {activeTab === "enquiries" && (
        <div className="space-y-6">
          {/* Search & Filter Toolbar */}
          <div className="bg-white rounded-[12px] border border-[#E6E6E6] p-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex-1 min-w-[200px] relative">
                <Search className="w-4 h-4 text-[#5F5F5F] absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  aria-label="Search enquiries"
                  value={enquirySearch}
                  onChange={(e) => {
                    setEnquirySearch(e.target.value);
                    setPage(0);
                  }}
                  onKeyDown={(e) => e.key === "Enter" && loadEnquiries({ page: 0 })}
                  placeholder="Search customer, email, tour, or ENQ reference..."
                  className="w-full pl-9 pr-3 py-2 border border-[#E6E6E6] rounded-[8px] text-xs focus:outline-none focus:border-[#F26B1D]"
                />
              </div>
              <select
                aria-label="Filter by status"
                value={enquiryFilter}
                onChange={(e) => {
                  const v = e.target.value;
                  setEnquiryFilter(v);
                  setPage(0);
                  loadEnquiries({ status: v, page: 0 });
                }}
                className="px-3 py-2 border border-[#E6E6E6] rounded-[8px] text-xs bg-white"
              >
                <option value="">All statuses</option>
                <option value="new">New</option>
                <option value="in_review">In Review</option>
                <option value="contacted">Contacted</option>
                <option value="waiting">Waiting</option>
                <option value="waiting_customer">Waiting Customer</option>
                <option value="quoted">Quoted</option>
                <option value="booked">Booked</option>
                <option value="closed">Closed</option>
                <option value="closed_lost">Closed Lost</option>
                <option value="unqualified">Unqualified</option>
              </select>
              <select
                aria-label="Filter by assignee"
                value={enquiryAssignedFilter}
                onChange={(e) => {
                  const v = e.target.value;
                  setEnquiryAssignedFilter(v);
                  setPage(0);
                  loadEnquiries({ assigned_to: v, page: 0 });
                }}
                className="px-3 py-2 border border-[#E6E6E6] rounded-[8px] text-xs bg-white"
              >
                <option value="">All assignees</option>
                <option value="__unassigned__">Unassigned only</option>
                {assignableStaff.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.full_name}
                  </option>
                ))}
              </select>
              <select
                aria-label="Filter by contactability"
                value={enquiryContactableFilter}
                onChange={(e) => {
                  const v = e.target.value;
                  setEnquiryContactableFilter(v);
                  setPage(0);
                  loadEnquiries({ contactable: v, page: 0 });
                }}
                className="px-3 py-2 border border-[#E6E6E6] rounded-[8px] text-xs bg-white"
              >
                <option value="">All visitors & leads</option>
                <option value="1">Contactable leads only</option>
                <option value="0">Guest browsing only</option>
              </select>
              <select
                aria-label="Sort enquiries"
                value={enquirySort}
                onChange={(e) => {
                  const v = e.target.value;
                  setEnquirySort(v);
                  setPage(0);
                  loadEnquiries({ sort: v, page: 0 });
                }}
                className="px-3 py-2 border border-[#E6E6E6] rounded-[8px] text-xs bg-white"
              >
                <option value="newest">Newest first</option>
                <option value="oldest">Oldest first</option>
                <option value="follow_up">Follow-up due</option>
                <option value="updated">Last updated</option>
              </select>
              <button
                type="button"
                onClick={() => loadEnquiries({ page: 0 })}
                className="px-4 py-2 rounded-[999px] border border-[#E6E6E6] bg-white text-xs font-semibold hover:border-[#111111] cursor-pointer"
              >
                Apply Filter
              </button>
            </div>
          </div>

          <div
            ref={workspaceRef}
            data-mobile-view={selectedEnquiry ? "detail" : "list"}
            style={
              workspaceHeight
                ? ({ "--staff-workspace-height": workspaceHeight } as CSSProperties)
                : undefined
            }
            className="staff-enquiry-workspace grid grid-cols-1 lg:grid-cols-12 gap-6"
          >
            {/* Master List */}
            <div className={`staff-enquiry-list-card ${selectedEnquiry ? "lg:col-span-7" : "lg:col-span-12"} bg-white rounded-[12px] border border-[#E6E6E6] overflow-hidden`}>
              <div className="px-5 py-3.5 border-b border-[#E6E6E6] bg-gray-50 flex items-center justify-between shrink-0">
                <h3 className="font-semibold text-xs uppercase tracking-wider text-[#5F5F5F]">
                  Traveller Enquiries ({totalEnquiries})
                </h3>
                <span className="text-[11px] text-[#5F5F5F]">Click any row to manage</span>
              </div>

              {enquiries.length === 0 ? (
                <div className="p-12 text-center text-xs text-[#5F5F5F]">No enquiries match the selected filters.</div>
              ) : (
                <div
                  tabIndex={0}
                  role="region"
                  aria-label="Enquiry list"
                  className="staff-enquiry-list-scroll divide-y divide-[#E6E6E6] focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[#F26B1D]"
                >
                  {enquiries.map((row) => {
                    const isSelected = selectedEnquiry?.id === row.id;
                    return (
                      <button
                        key={row.id}
                        type="button"
                        onClick={() => openEnquiryDetail(row.id)}
                        className={`w-full text-left px-5 py-4 hover:bg-gray-50 transition-colors cursor-pointer block ${
                          isSelected ? "bg-[#F26B1D]/5 border-l-4 border-[#F26B1D]" : ""
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3 mb-1.5">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-mono text-xs font-bold text-[#111111]">
                                {row.reference || row.id.slice(0, 8)}
                              </span>
                              <span className={`px-2 py-0.5 rounded-[999px] border text-[11px] font-semibold capitalize ${statusBadgeStyle(row.status)}`}>
                                {(row.status || "new").replace("_", " ")}
                              </span>
                              {row.is_contactable ? (
                                <span className="px-2 py-0.5 rounded-[999px] text-[10px] font-semibold bg-[#4CA64C]/15 text-[#276327]">
                                  Contactable
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded-[999px] text-[10px] font-medium bg-gray-100 text-[#5F5F5F]">
                                  Guest only
                                </span>
                              )}
                              {row.mock_booking_status && (
                                <span className="px-2 py-0.5 rounded-[999px] text-[10px] font-semibold bg-[#14837B]/15 text-[#14837B]">
                                  Mock Booking: {row.mock_booking_status}
                                </span>
                              )}
                            </div>
                            <p className="text-sm font-semibold text-[#111111] mt-1 truncate">
                              {row.tour_name || "Sri Lanka Journey"}
                            </p>
                          </div>
                          <div className="text-right shrink-0">
                            {row.quoted_total_usd ? (
                              <span className="text-xs font-bold text-[#F26B1D]">USD {row.quoted_total_usd.toLocaleString()}</span>
                            ) : (
                              <span className="text-[11px] font-medium text-[#855800]">Needs quote</span>
                            )}
                            <p className="text-[11px] text-[#5F5F5F] mt-0.5">{formatTs(row.created)}</p>
                          </div>
                        </div>

                        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-[#5F5F5F] mt-2">
                          <div className="flex items-center gap-3 flex-wrap">
                            <span className="font-medium text-[#111111]">{row.traveller_name || "Guest traveller"}</span>
                            {row.travel_date && <span>Date: {row.travel_date}</span>}
                            {row.adults && (
                              <span>
                                {row.adults} Adults{row.children_count ? `, ${row.children_count} Ch` : ""}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            {row.assigned_name && (
                              <span className="text-[11px] font-medium text-[#14837B]">Assigned: {row.assigned_name}</span>
                            )}
                            {row.follow_up_date && (
                              <span className="text-[11px] font-medium text-[#855800]">Due: {row.follow_up_date}</span>
                            )}
                          </div>
                        </div>
                        <p className="text-[11px] text-[#5F5F5F] mt-1">{row.human_reason || row.reason}</p>
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Pagination */}
              <div className="px-5 py-3 border-t border-[#E6E6E6] bg-gray-50 flex items-center justify-between text-xs">
                <span className="text-[#5F5F5F]">
                  Page {page + 1} of {totalPages}
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={page === 0}
                    onClick={() => {
                      const p = Math.max(0, page - 1);
                      setPage(p);
                      loadEnquiries({ page: p });
                    }}
                    className="px-3 py-1 rounded-[999px] border border-[#E6E6E6] bg-white disabled:opacity-40 cursor-pointer"
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    disabled={page + 1 >= totalPages}
                    onClick={() => {
                      const p = page + 1;
                      setPage(p);
                      loadEnquiries({ page: p });
                    }}
                    className="px-3 py-1 rounded-[999px] border border-[#E6E6E6] bg-white disabled:opacity-40 cursor-pointer"
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>

            {/* Detail Drawer */}
            {selectedEnquiry && (
              <div
                ref={detailRef}
                tabIndex={0}
                role="region"
                aria-label="Enquiry details"
                className="staff-enquiry-detail lg:col-span-5 bg-white rounded-[12px] border border-[#E6E6E6] p-6 space-y-5 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[#F26B1D]"
              >
                <button
                  type="button"
                  onClick={() => setSelectedEnquiry(null)}
                  className="staff-enquiry-back px-3 py-1.5 rounded-[999px] border border-[#E6E6E6] text-xs font-semibold text-[#111111] hover:bg-gray-50 cursor-pointer"
                >
                  ← Back to enquiries
                </button>
                <div className="flex items-start justify-between gap-3 border-b border-[#E6E6E6] pb-4">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs font-bold text-[#F26B1D]">{selectedEnquiry.reference}</span>
                      <span className={`px-2 py-0.5 rounded-[999px] border text-[11px] font-semibold capitalize ${statusBadgeStyle(selectedEnquiry.status)}`}>
                        {(selectedEnquiry.status || "new").replace("_", " ")}
                      </span>
                    </div>
                    <h3 className="font-bold text-base text-[#111111] mt-1">{selectedEnquiry.tour_name}</h3>
                    <p className="text-xs text-[#5F5F5F] mt-0.5">{selectedEnquiry.human_reason}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedEnquiry(null)}
                    className="p-1.5 rounded-full hover:bg-gray-100 text-[#5F5F5F] cursor-pointer"
                    aria-label="Close detail"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {detailLoading ? (
                  <p className="text-xs text-[#5F5F5F] py-6 text-center">Loading details...</p>
                ) : (
                  <>
                    {/* Customer Contact Card */}
                    <div className="bg-gray-50 rounded-[12px] p-4 border border-[#E6E6E6] space-y-1.5 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-[11px] uppercase tracking-wider text-[#5F5F5F]">Traveller Information</span>
                        <span className="text-[11px] font-medium text-[#14837B]">{selectedEnquiry.traveller_type}</span>
                      </div>
                      <p className="font-semibold text-sm text-[#111111]">{selectedEnquiry.traveller_name}</p>
                      {selectedEnquiry.is_contactable ? (
                        <div className="space-y-1 pt-1">
                          <p>
                            Email:{" "}
                            <a href={`mailto:${selectedEnquiry.traveller_email}`} className="text-[#F26B1D] font-medium hover:underline">
                              {selectedEnquiry.traveller_email}
                            </a>
                          </p>
                          {selectedEnquiry.traveller_phone && (
                            <p>
                              Phone:{" "}
                              <a href={`tel:${selectedEnquiry.traveller_phone}`} className="text-[#111111] font-medium hover:underline">
                                {selectedEnquiry.traveller_phone}
                              </a>
                            </p>
                          )}
                        </div>
                      ) : (
                        <p className="text-[#5F5F5F] italic">Anonymous browsing session — no email or phone submitted.</p>
                      )}
                    </div>

                    {/* Trip Configuration */}
                    <div className="grid grid-cols-2 gap-3 text-xs bg-white border border-[#E6E6E6] rounded-[12px] p-4">
                      <div>
                        <span className="text-[#5F5F5F] block">Tour Code</span>
                        <span className="font-semibold text-[#111111]">{selectedEnquiry.tour_id || "Custom / General"}</span>
                      </div>
                      <div>
                        <span className="text-[#5F5F5F] block">Travel Date</span>
                        <span className="font-semibold text-[#111111]">{selectedEnquiry.travel_date || "Flexible"}</span>
                      </div>
                      <div>
                        <span className="text-[#5F5F5F] block">Party</span>
                        <span className="font-semibold text-[#111111]">
                          {selectedEnquiry.adults ?? "—"} Adults
                          {selectedEnquiry.children_count ? `, ${selectedEnquiry.children_count} Children` : ""}
                        </span>
                      </div>
                      <div>
                        <span className="text-[#5F5F5F] block">Child / Infant Ages</span>
                        <span className="font-semibold text-[#111111]">
                          {selectedEnquiry.child_ages?.length ? selectedEnquiry.child_ages.join(", ") : "None"}
                        </span>
                      </div>
                      <div>
                        <span className="text-[#5F5F5F] block">Created</span>
                        <span className="font-medium text-[#111111]">{formatTs(selectedEnquiry.created)}</span>
                      </div>
                      <div>
                        <span className="text-[#5F5F5F] block">Last Updated</span>
                        <span className="font-medium text-[#111111]">{formatTs(selectedEnquiry.updated_at)}</span>
                      </div>
                      {selectedEnquiry.special_requests && (
                        <div className="col-span-2 pt-2 border-t border-[#E6E6E6]">
                          <span className="text-[#5F5F5F] block mb-0.5">Customer Requests / Notes</span>
                          <p className="text-[#111111]">{selectedEnquiry.special_requests}</p>
                        </div>
                      )}
                    </div>

                    {/* Internal Financials (Staff Only) */}
                    {selectedEnquiry.finance ? (
                      <div className="bg-[#F5B700]/10 border border-[#F5B700]/40 rounded-[12px] p-4 text-xs space-y-2">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <span className="font-semibold text-[11px] uppercase tracking-wider text-[#111111]">
                            Verified Quote & Margin (Staff Only)
                          </span>
                          {selectedEnquiry.quote && (
                            <span className="font-mono text-[11px] text-[#5F5F5F]">
                              Quote: {selectedEnquiry.quote}
                            </span>
                          )}
                          {selectedEnquiry.mock_booking_status && (
                            <span className="px-2 py-0.5 rounded-[999px] bg-[#4CA64C]/20 text-[#276327] font-semibold capitalize">
                              Booking: {selectedEnquiry.mock_booking_status}
                            </span>
                          )}
                        </div>
                        <div className="grid grid-cols-2 gap-2 pt-1">
                          <div>
                            <span className="text-[#5F5F5F]">Selling Total:</span>{" "}
                            <strong>USD {selectedEnquiry.finance.total}</strong>
                          </div>
                          <div>
                            <span className="text-[#5F5F5F]">Deposit:</span>{" "}
                            <strong>USD {selectedEnquiry.finance.deposit}</strong>
                          </div>
                          <div>
                            <span className="text-[#5F5F5F]">Buy Cost:</span>{" "}
                            <strong>LKR {Number(selectedEnquiry.finance.cost_lkr || 0).toLocaleString()}</strong>
                          </div>
                          <div>
                            <span className="text-[#5F5F5F]">Gross Profit:</span>{" "}
                            <strong>{Number(selectedEnquiry.finance.gross_profit_pct || 0).toFixed(2)}%</strong>
                          </div>
                        </div>
                        {selectedEnquiry.mock_booking_reference && (
                          <p className="text-[11px] font-mono text-[#276327] pt-1">
                            Mock Booking Ref: {selectedEnquiry.mock_booking_reference}
                          </p>
                        )}
                      </div>
                    ) : (
                      <div className="bg-gray-50 border border-[#E6E6E6] rounded-[12px] p-3 text-xs text-[#5F5F5F]">
                        <strong>Specialist Pricing Required:</strong> {selectedEnquiry.human_reason}
                      </div>
                    )}

                    {/* Quote Revisions History */}
                    {selectedEnquiry.quote_history && selectedEnquiry.quote_history.length > 0 && (
                      <div className="bg-white border border-[#E6E6E6] rounded-[12px] p-3 text-xs space-y-2">
                        <span className="font-semibold text-[11px] uppercase tracking-wider text-[#5F5F5F] block">
                          Quotation Revisions ({selectedEnquiry.quote_history.length})
                        </span>
                        <div className="space-y-1.5 max-h-32 overflow-y-auto">
                          {selectedEnquiry.quote_history.map((qh) => (
                            <div
                              key={qh.id}
                              className={`flex items-center justify-between px-2.5 py-1.5 rounded-[8px] ${
                                qh.is_latest ? "bg-[#F26B1D]/10 font-semibold" : "bg-gray-50 text-[#5F5F5F]"
                              }`}
                            >
                              <span>
                                {qh.id} • {qh.date} • {qh.adults}A{qh.ages.length ? ` + ${qh.ages.length}C` : ""}
                              </span>
                              <span>
                                USD {qh.total} ({Number(qh.gross_profit_pct || 0).toFixed(1)}% GP)
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Follow-Up Form */}
                    <form onSubmit={handleFollowUp} className="space-y-3 border-t border-[#E6E6E6] pt-4">
                      <h4 className="font-semibold text-xs uppercase tracking-wider text-[#5F5F5F]">Follow-Up Management</h4>
                      {enquiryActionMsg.text && (
                        <div
                          role="status"
                          className={`p-2.5 rounded-[8px] text-xs ${
                            enquiryActionMsg.type === "success"
                              ? "bg-[#4CA64C]/15 text-[#276327] border border-[#4CA64C]/30"
                              : "bg-[#E5533D]/10 text-[#111111] border border-[#E5533D]/40"
                          }`}
                        >
                          {enquiryActionMsg.text}
                        </div>
                      )}
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label htmlFor="detail-status" className="text-xs font-medium block mb-1">
                            Status
                          </label>
                          <select
                            id="detail-status"
                            value={statusInput}
                            disabled={enquiryBusy}
                            onChange={(e) => setStatusInput(e.target.value)}
                            className="w-full px-2.5 py-2 border border-[#E6E6E6] rounded-[8px] text-xs bg-white"
                          >
                            <option value="new">New</option>
                            <option value="in_review">In Review</option>
                            <option value="contacted">Contacted</option>
                            <option value="waiting">Waiting</option>
                            <option value="waiting_customer">Waiting Customer</option>
                            <option value="quoted">Quoted</option>
                            <option value="booked">Booked</option>
                            <option value="closed">Closed</option>
                            <option value="closed_lost">Closed Lost</option>
                            <option value="unqualified">Unqualified</option>
                          </select>
                        </div>
                        <div>
                          <label htmlFor="detail-assignee" className="text-xs font-medium block mb-1">
                            Assign Staff
                          </label>
                          <select
                            id="detail-assignee"
                            value={assignedStaffInput}
                            disabled={enquiryBusy}
                            onChange={(e) => setAssignedStaffInput(e.target.value)}
                            className="w-full px-2.5 py-2 border border-[#E6E6E6] rounded-[8px] text-xs bg-white"
                          >
                            <option value="">Unassigned</option>
                            {assignableStaff.map((s) => (
                              <option key={s.id} value={s.id}>
                                {s.full_name} ({s.role})
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                      <div>
                        <label htmlFor="detail-followup-date" className="text-xs font-medium block mb-1">
                          Follow-up Due Date
                        </label>
                        <input
                          id="detail-followup-date"
                          type="date"
                          value={followUpDateInput}
                          disabled={enquiryBusy}
                          onChange={(e) => setFollowUpDateInput(e.target.value)}
                          className="w-full px-2.5 py-2 border border-[#E6E6E6] rounded-[8px] text-xs bg-white"
                        />
                      </div>
                      <div>
                        <label htmlFor="detail-note" className="text-xs font-medium block mb-1">
                          Add Private Note (no email/phone PII)
                        </label>
                        <textarea
                          id="detail-note"
                          rows={2}
                          value={noteInput}
                          disabled={enquiryBusy}
                          onChange={(e) => setNoteInput(e.target.value)}
                          placeholder="Record operational update or follow-up outcome..."
                          className="w-full px-2.5 py-2 border border-[#E6E6E6] rounded-[8px] text-xs resize-none"
                        />
                      </div>
                      <button
                        type="submit"
                        disabled={enquiryBusy}
                        className="w-full py-2 px-4 rounded-[999px] bg-[#F26B1D] text-white font-semibold text-xs hover:bg-[#d95a12] transition-colors cursor-pointer disabled:opacity-60"
                      >
                        {enquiryBusy ? "Saving..." : "Save Follow-Up Update"}
                      </button>
                    </form>

                    {/* Notes History */}
                    <div className="border-t border-[#E6E6E6] pt-4">
                      <h4 className="font-semibold text-xs uppercase tracking-wider text-[#5F5F5F] mb-2">
                        Staff Notes ({Array.isArray(selectedEnquiry.notes) ? selectedEnquiry.notes.length : (selectedEnquiry.notes ? 1 : 0)})
                      </h4>
                      {Array.isArray(selectedEnquiry.notes) && selectedEnquiry.notes.length > 0 ? (
                        <div className="space-y-2 max-h-40 overflow-y-auto">
                          {selectedEnquiry.notes.map((n, idx) => (
                            <div key={idx} className="p-2.5 rounded-[8px] bg-gray-50 border border-[#E6E6E6] text-xs">
                              <p className="text-[#111111]">{n.body}</p>
                              <p className="text-[10px] text-[#5F5F5F] mt-1">
                                {n.actor} • {formatTs(n.created)}
                              </p>
                            </div>
                          ))}
                        </div>
                      ) : typeof (selectedEnquiry.notes as unknown) === "string" && Boolean((selectedEnquiry.notes as unknown as string).trim()) ? (
                        <div className="p-2.5 rounded-[8px] bg-gray-50 border border-[#E6E6E6] text-xs">
                          <p className="text-[#111111]">{selectedEnquiry.notes as unknown as string}</p>
                        </div>
                      ) : (
                        <p className="text-xs text-[#5F5F5F] italic">No operational notes yet.</p>
                      )}
                    </div>

                    {/* Trace Inspector */}
                    <div className="border-t border-[#E6E6E6] pt-3 text-[11px] text-[#5F5F5F] space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-mono">Trace: {selectedEnquiry.trace?.slice(0, 12)}...</span>
                        <div className="flex items-center gap-3">
                          <a
                            href={`/api/staff/traces/${selectedEnquiry.trace}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-[#14837B] font-semibold hover:underline"
                          >
                            Trace JSON ↗
                          </a>
                          <button
                            type="button"
                            onClick={() => setShowTrace(!showTrace)}
                            className="text-[#F26B1D] font-semibold hover:underline cursor-pointer"
                          >
                            {showTrace ? "Hide Trace" : "Inspect Trace"}
                          </button>
                        </div>
                      </div>
                      {showTrace && (
                        <pre className="p-2.5 bg-[#111111] text-gray-100 rounded-[8px] text-[10px] overflow-x-auto max-h-48">
                          {JSON.stringify(selectedEnquiry.events, null, 2)}
                        </pre>
                      )}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* CONTENT REVIEW TAB */}
      {activeTab === "content" && (
        <div className="space-y-6">
          <div className="bg-white rounded-[12px] border border-[#E6E6E6] p-6">
            <h2 className="text-base font-bold text-[#111111] mb-1">Generate AI-Assisted Journey Draft</h2>
            <p className="text-xs text-[#5F5F5F] mb-4">
              Drafts use only published destination materials.{" "}
              <strong className="text-[#111111]">Human Approval Rule:</strong> Only an authenticated Approver can publish drafts to Mira.
            </p>
            {draftMsg && (
              <div role="status" className="p-3 rounded-[8px] text-xs mb-4 bg-[#F5B700]/15 text-[#111111] border border-[#F5B700]/40">
                {draftMsg}
              </div>
            )}
            <form onSubmit={handleGenerateDraft} className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                required
                value={draftPrompt}
                disabled={draftBusy}
                onChange={(e) => setDraftPrompt(e.target.value)}
                placeholder="Prepare a private Hill Country journey using published Ella material"
                className="flex-1 text-sm px-3 py-2.5 rounded-[8px] border border-[#E6E6E6] focus:outline-none focus:border-[#F26B1D]"
              />
              <button
                type="submit"
                disabled={draftBusy}
                className="px-6 py-2.5 rounded-[999px] bg-[#F26B1D] text-white font-semibold text-sm hover:bg-[#d95a12] transition-colors cursor-pointer disabled:opacity-60 whitespace-nowrap"
              >
                {draftBusy ? "Generating..." : "Create Draft"}
              </button>
            </form>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Drafts List */}
            <div className="bg-white rounded-[12px] border border-[#E6E6E6] overflow-hidden">
              <div className="px-5 py-3.5 border-b border-[#E6E6E6] bg-gray-50 font-semibold text-xs uppercase tracking-wider text-[#5F5F5F]">
                Content Drafts ({drafts.length})
              </div>
              <div className="divide-y divide-[#E6E6E6] max-h-[500px] overflow-y-auto">
                {drafts.length === 0 ? (
                  <p className="p-8 text-xs text-[#5F5F5F] text-center">No drafts created yet.</p>
                ) : (
                  drafts.map((d) => (
                    <button
                      key={d.id}
                      type="button"
                      onClick={() => setSelectedDraft(d)}
                      className={`w-full text-left p-4 hover:bg-gray-50 transition-colors cursor-pointer block ${
                        selectedDraft?.id === d.id ? "bg-[#F26B1D]/5 border-l-4 border-[#F26B1D]" : ""
                      }`}
                    >
                      <div className="flex justify-between items-start gap-2 mb-1">
                        <span className="font-semibold text-sm text-[#111111]">{d.title}</span>
                        <span
                          className={`text-[11px] px-2 py-0.5 rounded-[999px] font-semibold uppercase ${
                            d.status === "published"
                              ? "bg-[#4CA64C]/15 text-[#276327]"
                              : d.status === "approved"
                              ? "bg-[#3A8DDE]/15 text-[#175C9E]"
                              : d.status === "rejected"
                              ? "bg-[#E5533D]/15 text-[#9C2B1A]"
                              : "bg-[#F5B700]/15 text-[#855800]"
                          }`}
                        >
                          {d.status}
                        </span>
                      </div>
                      <p className="text-xs text-[#5F5F5F]">
                        Author: {d.author} • Source: {d.source} • {formatTs(d.created)}
                      </p>
                    </button>
                  ))
                )}
              </div>
            </div>

            {/* Draft Preview & Approver Actions */}
            <div className="bg-white rounded-[12px] border border-[#E6E6E6] p-6">
              {selectedDraft ? (
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between items-start gap-2">
                      <h3 className="text-lg font-bold text-[#111111]">{selectedDraft.title}</h3>
                      <span className="text-xs px-2.5 py-0.5 rounded-[999px] font-mono bg-gray-100 text-[#111111]">
                        {selectedDraft.id}
                      </span>
                    </div>
                    <p className="text-xs text-[#5F5F5F] mt-1">
                      Status: <strong className="capitalize text-[#111111]">{selectedDraft.status}</strong> • Author: {selectedDraft.author}
                    </p>
                  </div>

                  <div className="bg-gray-50 p-4 rounded-[12px] text-xs text-[#111111] max-h-60 overflow-y-auto whitespace-pre-wrap border border-[#E6E6E6] leading-relaxed">
                    {selectedDraft.body}
                  </div>

                  {selectedDraft.review_notes && (
                    <div className="bg-[#F5B700]/10 p-3 rounded-[8px] border border-[#F5B700]/40 text-xs">
                      <strong>Review Notes:</strong> {selectedDraft.review_notes} (by {selectedDraft.reviewer})
                    </div>
                  )}

                  {currentUser.role !== "approver" && selectedDraft.status !== "published" && (
                    <div className="p-3 rounded-[8px] bg-gray-50 border border-[#E6E6E6] text-xs text-[#5F5F5F]">
                      <strong>Approver Required:</strong> Your current role is <strong className="uppercase">{currentUser.role}</strong>. Only an{" "}
                      <strong>Approver</strong> account may review or publish drafts.
                    </div>
                  )}

                  {currentUser.role === "approver" && selectedDraft.status !== "published" && (
                    <div className="pt-4 border-t border-[#E6E6E6] space-y-3">
                      <div>
                        <label htmlFor="draft-review-notes" className="text-xs font-semibold text-[#111111] block mb-1">
                          Reviewer Feedback / Revision Notes
                        </label>
                        <input
                          id="draft-review-notes"
                          type="text"
                          value={reviewNotes}
                          onChange={(e) => setReviewNotes(e.target.value)}
                          placeholder="Optional notes for review decision..."
                          className="w-full text-xs p-2.5 rounded-[8px] border border-[#E6E6E6]"
                        />
                      </div>

                      <div className="flex gap-2 flex-wrap">
                        <button
                          type="button"
                          onClick={() => handleReviewDraft("request_revision")}
                          disabled={draftBusy}
                          className="px-3 py-1.5 rounded-[999px] border border-[#F5B700] text-xs font-semibold text-[#111111] cursor-pointer"
                        >
                          Request Revision
                        </button>
                        <button
                          type="button"
                          onClick={() => handleReviewDraft("reject")}
                          disabled={draftBusy}
                          className="px-3 py-1.5 rounded-[999px] border border-[#E5533D] text-xs font-semibold text-[#9C2B1A] cursor-pointer"
                        >
                          Reject Draft
                        </button>
                        <button
                          type="button"
                          onClick={() => handleReviewDraft("approve")}
                          disabled={draftBusy}
                          className="px-3 py-1.5 rounded-[999px] border border-[#3A8DDE] text-xs font-semibold text-[#175C9E] cursor-pointer"
                        >
                          Approve Content
                        </button>
                        <button
                          type="button"
                          onClick={handlePublishDraft}
                          disabled={draftBusy}
                          className="px-4 py-1.5 rounded-[999px] bg-[#F26B1D] text-white text-xs font-semibold hover:bg-[#d95a12] ml-auto cursor-pointer"
                        >
                          Approve & Publish to Mira
                        </button>
                      </div>
                    </div>
                  )}

                  {selectedDraft.status === "published" && (
                    <div className="p-3 bg-[#4CA64C]/15 text-[#276327] rounded-[8px] text-xs border border-[#4CA64C]/30">
                      Published and live for traveller retrieval at <code>/api/sources/{selectedDraft.id}</code>.
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-[#5F5F5F] text-center py-12">Select a draft to preview and review.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* USER ADMINISTRATION TAB (ADMIN ONLY) */}
      {activeTab === "users" && currentUser.role === "admin" && (
        <div className="space-y-6">
          <div className="flex justify-between items-center flex-wrap gap-4 bg-white p-4 rounded-[12px] border border-[#E6E6E6]">
            <h2 className="text-sm font-bold text-[#111111]">User Role & Account Administration</h2>
            <div className="flex gap-2">
              <input
                type="text"
                aria-label="Search users"
                placeholder="Search user email or name..."
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && loadUsers()}
                className="bg-white border border-[#E6E6E6] rounded-[8px] px-3 py-1.5 text-xs w-60"
              />
              <button
                type="button"
                onClick={loadUsers}
                className="px-4 py-1.5 rounded-[999px] border border-[#E6E6E6] text-xs font-semibold cursor-pointer"
              >
                Search
              </button>
            </div>
          </div>

          {userMsg && (
            <div role="status" className="p-3 rounded-[8px] text-xs bg-[#4CA64C]/15 text-[#276327] border border-[#4CA64C]/30">
              {userMsg}
            </div>
          )}

          <div className="bg-white rounded-[12px] border border-[#E6E6E6] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#E6E6E6] bg-gray-50 text-[#5F5F5F]">
                    <th className="p-3">User</th>
                    <th className="p-3">Role</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Created</th>
                    <th className="p-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E6E6E6]">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-50">
                      <td className="p-3">
                        <p className="font-semibold text-sm text-[#111111]">{u.full_name}</p>
                        <p className="text-xs text-[#5F5F5F]">{u.email}</p>
                      </td>
                      <td className="p-3">
                        <select
                          aria-label={`Role for ${u.email}`}
                          value={u.role}
                          disabled={userBusy}
                          onChange={(e) => handleUpdateUser(u.id, { role: e.target.value })}
                          className="text-xs p-1.5 rounded-[8px] border border-[#E6E6E6] bg-white font-semibold"
                        >
                          <option value="traveller">Traveller</option>
                          <option value="staff">Staff</option>
                          <option value="approver">Approver</option>
                          <option value="admin">Admin</option>
                        </select>
                      </td>
                      <td className="p-3">
                        <span
                          className={`text-[11px] px-2 py-0.5 rounded-[999px] font-semibold uppercase ${
                            u.status === "active" ? "bg-[#4CA64C]/15 text-[#276327]" : "bg-[#E5533D]/15 text-[#9C2B1A]"
                          }`}
                        >
                          {u.status}
                        </span>
                      </td>
                      <td className="p-3 text-[#5F5F5F] whitespace-nowrap">{formatTs(u.created_at)}</td>
                      <td className="p-3 text-right">
                        <button
                          type="button"
                          disabled={userBusy}
                          onClick={() =>
                            handleUpdateUser(u.id, {
                              status: u.status === "active" ? "deactivated" : "active",
                            })
                          }
                          className="px-3 py-1 rounded-[999px] border border-[#E6E6E6] text-xs font-medium cursor-pointer hover:border-[#111111]"
                        >
                          {u.status === "active" ? "Deactivate" : "Activate"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* RATE PREVIEW TAB (READ-ONLY) */}
      {activeTab === "preview" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-5 bg-white rounded-[12px] border border-[#E6E6E6] p-6 space-y-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[#14837B]">Read-Only Verification</p>
              <h2 className="text-sm font-bold text-[#111111] mt-0.5">Tour Rate Preview Calculator</h2>
              <p className="text-xs text-[#5F5F5F] mt-1">
                Evaluates the authoritative workbook pricing engine without saving any quote, enquiry, or booking.
              </p>
            </div>
            <form onSubmit={handleRunPreview} className="space-y-3">
              <div>
                <label htmlFor="preview-tour" className="text-xs font-medium block mb-1">Tour</label>
                <select
                  id="preview-tour"
                  value={previewTourId}
                  onChange={(e) => setPreviewTourId(e.target.value)}
                  className="w-full px-3 py-2 border border-[#E6E6E6] rounded-[8px] text-xs bg-white"
                >
                  {(previewTours.length > 0
                    ? previewTours
                    : [
                        { id: "T01", title: "Sigiriya and Minneriya Day Tour from Kandy" },
                        { id: "T08", title: "Highlights of Sri Lanka" },
                        { id: "T09", title: "Cultural Triangle Sri Lanka Package" },
                        { id: "T12", title: "Treasures of Sri Lanka" },
                      ]
                  ).map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.id} — {t.title}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="preview-date" className="text-xs font-medium block mb-1">Travel date</label>
                  <input
                    id="preview-date"
                    type="date"
                    required
                    value={previewDate}
                    onChange={(e) => setPreviewDate(e.target.value)}
                    className="w-full px-3 py-2 border border-[#E6E6E6] rounded-[8px] text-xs bg-white"
                  />
                </div>
                <div>
                  <label htmlFor="preview-adults" className="text-xs font-medium block mb-1">Adults</label>
                  <input
                    id="preview-adults"
                    type="number"
                    min={1}
                    max={100}
                    required
                    value={previewAdults}
                    onChange={(e) => setPreviewAdults(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-[#E6E6E6] rounded-[8px] text-xs bg-white"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="preview-child-ages" className="text-xs font-medium block mb-1">
                    Child ages (comma-separated)
                  </label>
                  <input
                    id="preview-child-ages"
                    type="text"
                    value={previewChildAgesText}
                    onChange={(e) => setPreviewChildAgesText(e.target.value)}
                    placeholder="e.g. 7, 10"
                    className="w-full px-3 py-2 border border-[#E6E6E6] rounded-[8px] text-xs bg-white"
                  />
                </div>
                <div>
                  <label htmlFor="preview-infants" className="text-xs font-medium block mb-1">Infants (&lt;2)</label>
                  <input
                    id="preview-infants"
                    type="number"
                    min={0}
                    max={30}
                    value={previewInfants}
                    onChange={(e) => setPreviewInfants(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-[#E6E6E6] rounded-[8px] text-xs bg-white"
                  />
                </div>
              </div>
              {previewError && (
                <div className="p-2.5 rounded-[8px] bg-red-50 border border-red-200 text-xs text-red-700" role="alert">
                  {previewError}
                </div>
              )}
              <button
                type="submit"
                disabled={previewBusy}
                className="w-full py-2.5 px-4 rounded-[999px] bg-[#F26B1D] text-white font-semibold text-xs hover:bg-[#d95a12] transition-colors cursor-pointer disabled:opacity-60"
              >
                {previewBusy ? "Calculating..." : "Run Rate Preview"}
              </button>
            </form>
          </div>

          <div className="lg:col-span-7 bg-white rounded-[12px] border border-[#E6E6E6] p-6 space-y-4">
            <div className="px-3 py-2 rounded-[8px] bg-[#14837B]/10 border border-[#14837B]/30 text-xs font-semibold text-[#14837B]">
              Pricing preview — not a saved quotation or booking.
            </div>

            {!previewResult ? (
              <p className="text-xs text-[#5F5F5F] py-8 text-center">
                Select a tour, travel date, and party configuration, then run a read-only rate preview.
              </p>
            ) : previewResult.outcome === "PRICE_VERIFIED" ? (
              <div className="space-y-4 text-xs">
                <div className="flex items-start justify-between gap-4 border-b border-[#E6E6E6] pb-3">
                  <div>
                    <span className="px-2 py-0.5 rounded-[999px] bg-[#4CA64C]/15 text-[#276327] font-semibold text-[11px]">
                      PRICE_VERIFIED
                    </span>
                    <h3 className="font-bold text-base text-[#111111] mt-1">
                      {previewResult.evaluated_config.tour_title}
                    </h3>
                    <p className="text-[#5F5F5F]">
                      {previewResult.evaluated_config.date} • {previewResult.evaluated_config.adults} adults
                      {previewResult.evaluated_config.child_ages.length > 0
                        ? ` • Child ages: ${previewResult.evaluated_config.child_ages.join(", ")}`
                        : ""}
                      {previewResult.evaluated_config.infants > 0
                        ? ` • ${previewResult.evaluated_config.infants} infant(s)`
                        : ""}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-[#5F5F5F] block">Selling Total</span>
                    <span className="text-xl font-bold text-[#F26B1D]">
                      USD {previewResult.total_usd?.toLocaleString()}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-gray-50 rounded-[8px] p-3 border border-[#E6E6E6]">
                  <div>
                    <span className="text-[#5F5F5F] block">Deposit</span>
                    <strong>USD {previewResult.deposit_usd?.toLocaleString()}</strong>
                  </div>
                  <div>
                    <span className="text-[#5F5F5F] block">Balance</span>
                    <strong>USD {previewResult.balance_usd?.toLocaleString()}</strong>
                  </div>
                  <div>
                    <span className="text-[#5F5F5F] block">Buy Cost (Staff)</span>
                    <strong>LKR {Number(previewResult.finance?.cost_lkr || 0).toLocaleString()}</strong>
                  </div>
                  <div>
                    <span className="text-[#5F5F5F] block">Gross Profit</span>
                    <strong>{Number(previewResult.finance?.gross_profit_pct || 0).toFixed(2)}%</strong>
                  </div>
                </div>

                {previewResult.rate_digest && (
                  <p className="text-[11px] font-mono text-[#5F5F5F]">
                    Workbook digest: {previewResult.rate_digest.slice(0, 16)}… • Clock: {previewResult.evaluated_config.as_of}
                  </p>
                )}
              </div>
            ) : (
              <div className="space-y-3 text-xs">
                <span className="px-2 py-0.5 rounded-[999px] bg-[#F5B700]/20 text-[#855800] font-semibold text-[11px]">
                  {previewResult.outcome}
                </span>
                <h3 className="font-bold text-sm text-[#111111]">
                  {previewResult.evaluated_config.tour_title} ({previewResult.evaluated_config.date})
                </h3>
                <p className="text-[#111111]">{previewResult.reason}</p>
                {previewResult.reason_code && (
                  <p className="text-[11px] font-mono text-[#5F5F5F]">
                    Reason code: {previewResult.reason_code}
                    {previewResult.rate_digest ? ` • Digest: ${previewResult.rate_digest.slice(0, 16)}…` : ""}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* AUDIT HISTORY TAB */}
      {activeTab === "audit" && (
        <div className="bg-white rounded-[12px] border border-[#E6E6E6] p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-sm font-bold text-[#111111]">Immutable Operations Audit Trail</h2>
            <button
              type="button"
              onClick={loadAudit}
              className="px-3 py-1.5 rounded-[999px] border border-[#E6E6E6] text-xs font-semibold cursor-pointer"
            >
              Refresh
            </button>
          </div>
          <p className="text-xs text-[#5F5F5F]">
            All privileged operations, role assignments, and publication transitions are immutably logged in SQLite.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#E6E6E6] text-[#5F5F5F]">
                  <th className="pb-2">ID</th>
                  <th className="pb-2">Timestamp</th>
                  <th className="pb-2">Actor</th>
                  <th className="pb-2">Operation</th>
                  <th className="pb-2">Target</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E6E6E6]/60">
                {auditRows.map((a) => (
                  <tr key={a.id} className="hover:bg-gray-50">
                    <td className="py-2.5 text-[#5F5F5F] font-mono">#{a.id}</td>
                    <td className="py-2.5 text-[#5F5F5F] whitespace-nowrap">{formatTs(a.created)}</td>
                    <td className="py-2.5 font-semibold text-[#111111]">{a.actor}</td>
                    <td className="py-2.5">
                      <span className="px-2 py-0.5 rounded-[999px] text-[11px] font-semibold bg-gray-100">{a.action}</span>
                    </td>
                    <td className="py-2.5 text-[#5F5F5F] font-mono">{a.target}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

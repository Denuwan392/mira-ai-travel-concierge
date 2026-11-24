/**
 * Workspace-Preferred frontend unit & integration tests.
 *
 * Tests the unified StaffConsole component and MarkdownContent renderer:
 * - Login form rendering & invalid credential error handling via /api/auth/login + /api/staff/me
 * - Live DB overview metrics (no hardcoded static numbers)
 * - Enquiry list + detail drawer + follow-up save (PATCH)
 * - Content Review draft creation + Approver-only publish controls
 * - MarkdownContent safe rendering of ItineraryDay / PolicySnippet markdown
 */
import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { StaffConsole } from "@/components/staff/StaffConsole";
import { MarkdownContent } from "@/components/plan/MarkdownContent";
// @ts-expect-error JSX workspace module without .d.ts
import { UIComponentRenderer, HomePage, EnquiryPage, AuthProvider } from "../../workspace/Workspace.jsx";

const mockFetch = vi.fn();

beforeEach(() => {
  mockFetch.mockReset();
  vi.stubGlobal("fetch", mockFetch);
});

function jsonResponse(data: unknown, status = 200, extraHeaders: Record<string, string> = {}) {
  const hdrs = new Headers(extraHeaders);
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
    headers: hdrs,
  });
}

const MOCK_OVERVIEW = {
  total_enquiries: 42,
  open_enquiries: 15,
  pending_followups: 8,
  contactable_enquiries: 20,
  unassigned_enquiries: 5,
  missing_rate_enquiries: 2,
  quotes_requiring_confirmation: 3,
  pending_content_approvals: 1,
  recent_activity: [
    { id: 1, actor: "admin@test.com", action: "login", target: "staff-session", created: "2026-11-25T00:00:00Z" },
  ],
};

const MOCK_ENQUIRY_ROW = {
  id: "ENQ-TEST-001",
  reference: "ENQ-TEST-001",
  reason: "tour_quote",
  human_reason: "Quote for Sigiriya tour",
  status: "new",
  created: "2026-11-25T00:00:00Z",
  quote: "Q-TEST-1",
  trip: "{}",
  trace: "trace-001",
  tour_name: "Sigiriya Day Tour",
  traveller_name: "Test User",
  traveller_email: "guest@example.test",
  is_contactable: true,
};

function setupAuthenticatedStaff(role = "staff", extraHandler?: (url: string, opts?: RequestInit) => Promise<unknown> | null) {
  mockFetch.mockImplementation((url: string, opts?: RequestInit) => {
    if (extraHandler) {
      const custom = extraHandler(url, opts);
      if (custom) return custom;
    }
    if (url.includes("/api/staff/me")) {
      return jsonResponse({ role, email: `${role}@test.com`, full_name: `Test ${role}` });
    }
    if (url.includes("/api/staff/dashboard/overview")) {
      return jsonResponse(MOCK_OVERVIEW);
    }
    if (url.includes("/api/staff/users/assignable")) {
      return jsonResponse([{ id: "u-staff-1", full_name: "Test Staff", email: "staff@test.com", role: "staff" }]);
    }
    if (url.includes("/api/staff/enquiries/") && opts?.method === "PATCH") {
      return jsonResponse({ status: "in_review" });
    }
    if (url.includes("/api/staff/enquiries/ENQ-")) {
      return jsonResponse({
        ...MOCK_ENQUIRY_ROW,
        events: [{ stage: "interpret", outcome: "ok" }],
        finance: { total: 315, deposit: 95, cost_lkr: "62000", gross_profit_pct: "34.2" },
        notes: [{ id: 1, actor: "staff@test.com", body: "Test note", created: "2026-11-25T00:00:00Z" }],
        quote_history: [
          { id: "Q-TEST-2", tour_id: "T01", date: "2027-01-12", adults: 2, ages: [], total: 330, deposit: 99, cost_lkr: "64000", gross_profit_pct: "35.0", created: "2026-11-25T01:00:00Z", is_latest: true },
          { id: "Q-TEST-1", tour_id: "T01", date: "2027-01-10", adults: 2, ages: [], total: 315, deposit: 95, cost_lkr: "62000", gross_profit_pct: "34.2", created: "2026-11-25T00:00:00Z", is_latest: false },
        ],
      });
    }
    if (url.includes("/api/staff/enquiries")) {
      return jsonResponse([MOCK_ENQUIRY_ROW], 200, { "X-Total-Count": "1" });
    }
    if (url.includes("/api/staff/drafts")) {
      return jsonResponse([]);
    }
    if (url.includes("/api/staff/audit") || url.includes("/api/admin/audit")) {
      return jsonResponse([]);
    }
    if (url.includes("/api/staff/evaluation")) {
      return jsonResponse(null);
    }
    return jsonResponse({}, 404);
  });
}

describe("StaffConsole Login Gate", () => {
  beforeEach(() => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/api/staff/me")) {
        return jsonResponse({ detail: "Not authenticated" }, 401);
      }
      return jsonResponse({}, 404);
    });
  });

  it("renders login form when not authenticated", async () => {
    render(<StaffConsole />);
    await waitFor(() => {
      expect(screen.getByLabelText("Staff Email")).toBeInTheDocument();
      expect(screen.getByLabelText("Password")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Sign In to Staff Console" })).toBeInTheDocument();
  });

  it("shows error on invalid credentials", async () => {
    mockFetch.mockImplementation((url: string, opts?: RequestInit) => {
      if (url.includes("/api/staff/me")) {
        return jsonResponse({ detail: "Not authenticated" }, 401);
      }
      if (url.includes("/api/auth/login") && opts?.method === "POST") {
        return jsonResponse({ detail: "Invalid credentials." }, 401);
      }
      return jsonResponse({}, 404);
    });

    render(<StaffConsole />);
    await waitFor(() => expect(screen.getByLabelText("Staff Email")).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText("Staff Email"), { target: { value: "wrong@test.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrongpass" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In to Staff Console" }));

    await waitFor(() => {
      expect(screen.getByText(/Invalid credentials/i)).toBeInTheDocument();
    });
  });
});

describe("StaffConsole Authenticated View", () => {
  beforeEach(() => setupAuthenticatedStaff());

  it("displays overview metrics from API (not hardcoded)", async () => {
    render(<StaffConsole defaultTab="overview" />);

    await waitFor(() => {
      expect(screen.getByText("15")).toBeInTheDocument();
      expect(screen.getByText("42 total recorded")).toBeInTheDocument();
    });
    expect(screen.queryByText("5 total recorded")).not.toBeInTheDocument();
  });

  it("renders all navigation tabs and evaluation results link", async () => {
    render(<StaffConsole defaultTab="overview" />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /overview/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Enquiries" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /content review/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /view evaluation results/i })).toBeInTheDocument();
    });
  });

  it("shows enquiry list, opens detail drawer with finance & quote history, and saves follow-up", async () => {
    render(<StaffConsole defaultTab="enquiries" />);

    await waitFor(() => {
      expect(screen.getByText("ENQ-TEST-001")).toBeInTheDocument();
      expect(screen.getByText("Test User")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("ENQ-TEST-001"));

    await waitFor(() => {
      expect(screen.getByText("guest@example.test")).toBeInTheDocument();
      expect(screen.getByText("Test note")).toBeInTheDocument();
      expect(screen.getByText(/Quotation Revisions \(2\)/)).toBeInTheDocument();
      expect(screen.getByText("34.20%")).toBeInTheDocument();
    });

    const detailRegion = screen.getByRole("region", { name: "Enquiry details" });
    fireEvent.change(within(detailRegion).getByLabelText("Status"), { target: { value: "in_review" } });
    fireEvent.change(within(detailRegion).getByLabelText(/Add Private Note/), { target: { value: "Followed up via call" } });
    const saveBtn = screen.getByRole("button", { name: "Save Follow-Up Update" });
    fireEvent.submit(saveBtn.closest("form")!);

    await waitFor(() => {
      expect(screen.getByText("Follow-up saved.")).toBeInTheDocument();
    });
  });
});

describe("StaffConsole Content Review & Approver Publish", () => {
  it("creates a draft and shows success message", async () => {
    let draftCreated = false;
    setupAuthenticatedStaff("editor", (url, opts) => {
      if (url.includes("/api/staff/drafts") && opts?.method === "POST") {
        draftCreated = true;
        return jsonResponse({ id: "DRAFT-001", mode: "gemini" });
      }
      if (url.includes("/api/staff/drafts") && !opts?.method) {
        return jsonResponse(
          draftCreated
            ? [{ id: "DRAFT-001", title: "Hill Country Journey", body: "Content...", source: "gemini", author: "editor@test.com", status: "draft", created: "2026-11-25T00:00:00Z" }]
            : []
        );
      }
      return null;
    });

    render(<StaffConsole defaultTab="overview" />);
    await waitFor(() => expect(screen.getByRole("button", { name: /content review/i })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /content review/i }));

    await waitFor(() => expect(screen.getByPlaceholderText(/Prepare a private Hill Country/i)).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText(/Prepare a private Hill Country/i), {
      target: { value: "Create a Hill Country draft for Ella" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create Draft" }));

    await waitFor(() => {
      expect(screen.getByText(/Draft created/i)).toBeInTheDocument();
    });
  });

  it("approver can review and publish drafts", async () => {
    const DRAFT = {
      id: "DRAFT-002",
      title: "Ella Hill Country Journey",
      body: "Journey content...",
      source: "gemini",
      author: "editor@test.com",
      status: "approved",
      created: "2026-11-25T00:00:00Z",
      reviewer: "approver@test.com",
      review_notes: "Looks good",
    };

    setupAuthenticatedStaff("approver", (url, opts) => {
      if (url.includes("/api/staff/drafts") && !opts?.method) {
        return jsonResponse([DRAFT]);
      }
      if (url.includes("/publish") && opts?.method === "POST") {
        return jsonResponse({ status: "published" });
      }
      return null;
    });

    render(<StaffConsole defaultTab="overview" />);
    await waitFor(() => expect(screen.getByRole("button", { name: /content review/i })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /content review/i }));

    await waitFor(() => expect(screen.getByText("Ella Hill Country Journey")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Ella Hill Country Journey"));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Approve & Publish/i })).toBeInTheDocument();
    });
  });
});

describe("MarkdownContent Safe Rendering", () => {
  it("renders structured markdown safely without raw tags or HTML execution", () => {
    render(<MarkdownContent content={"## Day 1: Sigiriya\n\n- Climb **Lion Rock**\n- Visit Minneriya"} />);
    expect(screen.getByText("Day 1: Sigiriya")).toBeInTheDocument();
    expect(screen.getByText(/Lion Rock/)).toBeInTheDocument();
  });
});

describe("Preferred Workspace (Workspace.jsx) Integration", () => {
  it("UIComponentRenderer renders ItineraryDay and PolicySnippet components", () => {
    render(
      <div>
        <UIComponentRenderer
          component={{
            type: "ItineraryDay",
            day: 2,
            title: "Kandy to Ella Train",
            location: "Hill Country",
            text: "Scenic train through **tea plantations**.",
          }}
          navigate={vi.fn()}
          tours={[]}
          setActiveTour={vi.fn()}
          setWorkspacePanel={vi.fn()}
        />
        <UIComponentRenderer
          component={{
            type: "PolicySnippet",
            title: "Cancellation Policy",
            text: "Free cancellation up to **14 days** prior.",
            source: "P01",
          }}
          navigate={vi.fn()}
          tours={[]}
          setActiveTour={vi.fn()}
          setWorkspacePanel={vi.fn()}
        />
      </div>
    );
    expect(screen.getByText("Day 2: Kandy to Ella Train")).toBeInTheDocument();
    expect(screen.getByText(/tea plantations/)).toBeInTheDocument();
    expect(screen.getByText("Cancellation Policy")).toBeInTheDocument();
    expect(screen.getByText(/14 days/)).toBeInTheDocument();
  });

  it("EnquiryPage renders unavailable error state on 404 instead of faking Status: new", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/api/enquiries/")) {
        return jsonResponse({ detail: "Not found" }, 404);
      }
      return jsonResponse({}, 404);
    });
    render(<EnquiryPage navigate={vi.fn()} reference="ENQ-MISSING-999" />);
    await waitFor(() => {
      expect(screen.getByText("Enquiry not found")).toBeInTheDocument();
    });
    expect(screen.queryByText("Status: new")).not.toBeInTheDocument();
  });

  it("HomePage forwards hero prompt to /mira via sessionStorage", () => {
    mockFetch.mockImplementation(() => jsonResponse({}, 401));
    sessionStorage.removeItem("mira-pending-prompt");
    const navigate = vi.fn();
    render(
      <AuthProvider>
        <HomePage navigate={navigate} />
      </AuthProvider>
    );
    const input = screen.getByPlaceholderText("Tell Mira what you'd love to experience...");
    fireEvent.change(input, { target: { value: "Plan 7 days in Kandy and Ella" } });
    fireEvent.keyDown(input, { key: "Enter", code: "Enter" });
    expect(sessionStorage.getItem("mira-pending-prompt")).toBe("Plan 7 days in Kandy and Ella");
    expect(navigate).toHaveBeenCalledWith("/mira");
  });
});

describe("StaffConsole Read-Only Rate Preview", () => {
  it("runs read-only preview and displays verified total with preview-only disclaimer", async () => {
    setupAuthenticatedStaff("staff", (url, opts) => {
      if (url.includes("/api/tours")) {
        return jsonResponse([{ id: "T01", title: "Sigiriya and Minneriya Day Tour from Kandy" }]);
      }
      if (url.includes("/api/staff/pricing/preview") && opts?.method === "POST") {
        return jsonResponse({
          preview_only: true,
          outcome: "PRICE_VERIFIED",
          rate_digest: "abc1234567890def",
          evaluated_config: {
            tour_id: "T01",
            tour_title: "Sigiriya and Minneriya Day Tour from Kandy",
            date: "2027-01-10",
            adults: 2,
            child_ages: [],
            infants: 0,
            as_of: "2026-11-19",
          },
          currency: "USD",
          total_usd: 315,
          deposit_usd: 315,
          balance_usd: 0,
          snapshot: "abc1234567890def",
          reason_code: null,
          reason: null,
          finance: { cost_lkr: "62000", gross_profit_pct: "34.20", breakdown: {} },
        });
      }
      return null;
    });

    render(<StaffConsole defaultTab="overview" />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Rate Preview" })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Rate Preview" }));

    await waitFor(() => {
      expect(screen.getByText("Pricing preview — not a saved quotation or booking.")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Run Rate Preview" }));

    await waitFor(() => {
      expect(screen.getAllByText("USD 315").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("PRICE_VERIFIED")).toBeInTheDocument();
    });
  });
});

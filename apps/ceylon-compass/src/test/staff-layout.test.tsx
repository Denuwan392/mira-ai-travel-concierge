import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { StaffConsole } from "@/components/staff/StaffConsole";

vi.mock("@tanstack/react-router", () => ({
  createFileRoute: () => () => ({ component: vi.fn() }),
  useRouter: () => ({ navigate: vi.fn() }),
  Link: ({ to, children, className, ...props }: any) => (
    <a href={to} className={className} {...props}>
      {children}
    </a>
  ),
}));

const mockEnquiries = [
  {
    id: "enq-001",
    reference: "ENQ-2026-00000001",
    tour_id: "T16",
    tour_name: "Cultural Triangle Tour",
    traveller_name: "John Doe",
    email: "john@example.com",
    travel_date: "2027-01-10",
    adults: 2,
    children_count: 3,
    status: "new",
    quoted_total_usd: null,
    reason: "Missing rates for season",
    human_reason: "Specialist review needed",
    is_contactable: true,
    created: "2026-11-20T10:00:00Z",
    assigned_to: null,
    assigned_name: null,
    follow_up_date: null,
  },
  {
    id: "enq-002",
    reference: "ENQ-2026-00000002",
    tour_id: "T01",
    tour_name: "Highlights of Sri Lanka",
    traveller_name: "Jane Smith",
    email: "jane@example.com",
    travel_date: "2026-12-05",
    adults: 2,
    children_count: 0,
    status: "in_review",
    quoted_total_usd: 3500,
    reason: "Standard quote",
    human_reason: "Awaiting client confirmation",
    is_contactable: true,
    created: "2026-11-21T12:00:00Z",
    assigned_to: "usr-01",
    assigned_name: "Alice Staff",
    follow_up_date: "2026-11-28",
  },
];

const mockEnquiryDetail = {
  ...mockEnquiries[0],
  notes: [{ actor: "Alice Staff", created: "2026-11-20T11:00:00Z", body: "Client requested 3 children aged 7, 7, 7." }],
  phone: "+1234567890",
  audit_trail: [],
};

describe("Staff Enquiry Management Layout and Scrolling Usability", () => {
  let originalFetch: typeof global.fetch;

  beforeEach(() => {
    originalFetch = global.fetch;
    const mockResponse = (data: unknown, status = 200, extraHeaders: Record<string, string> = {}) =>
      Promise.resolve({
        ok: status >= 200 && status < 300,
        status,
        headers: new Headers(extraHeaders),
        json: () => Promise.resolve(data),
        text: () => Promise.resolve(JSON.stringify(data)),
      });

    global.fetch = vi.fn().mockImplementation((url: string | URL | Request, init?: RequestInit) => {
      const urlStr = typeof url === "string" ? url : url.toString();

      if (urlStr.includes("/api/staff/me")) {
        return mockResponse({ role: "admin", email: "admin@ceyloncompass.com", full_name: "Admin User" });
      }
      if (urlStr.includes("/api/staff/dashboard/overview")) {
        return mockResponse({
          open_enquiries: 2,
          total_enquiries: 2,
          contactable_enquiries: 2,
          pending_followups: 1,
          missing_rate_enquiries: 1,
          unassigned_enquiries: 1,
          pending_content_approvals: 0,
        });
      }
      if (urlStr.includes("/api/staff/users/assignable")) {
        return mockResponse([{ id: "usr-01", full_name: "Alice Staff", email: "alice@ceyloncompass.com", role: "staff" }]);
      }
      if (urlStr.includes("/api/staff/evaluation")) {
        return mockResponse(null);
      }
      if (urlStr.includes("/api/staff/enquiries/enq-001")) {
        return mockResponse(mockEnquiryDetail);
      }
      if (urlStr.includes("/api/staff/enquiries")) {
        return mockResponse(mockEnquiries, 200, { "X-Total-Count": "2" });
      }
      return mockResponse({});
    }) as any;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders enquiry list within independent scroll container with accessibility attributes", async () => {
    render(<StaffConsole defaultTab="enquiries" />);

    // Wait for session check and data load
    await waitFor(() => {
      expect(screen.getByText("Traveller Enquiries (2)")).toBeInTheDocument();
    });

    const workspace = document.querySelector(".staff-enquiry-workspace");
    expect(workspace).not.toBeNull();
    expect(workspace).toHaveClass("grid");

    const listCard = document.querySelector(".staff-enquiry-list-card");
    expect(listCard).not.toBeNull();

    const listScroll = document.querySelector(".staff-enquiry-list-scroll");
    expect(listScroll).not.toBeNull();
    expect(listScroll?.getAttribute("role")).toBe("region");
    expect(listScroll?.getAttribute("aria-label")).toBe("Enquiry list");
    expect(listScroll?.getAttribute("tabindex")).toBe("0");

    // Both enquiry rows should be rendered
    expect(screen.getByText("ENQ-2026-00000001")).toBeInTheDocument();
    expect(screen.getByText("ENQ-2026-00000002")).toBeInTheDocument();
  });

  it("opens enquiry detail into independent scroll panel without losing list context", async () => {
    render(<StaffConsole defaultTab="enquiries" />);

    await waitFor(() => {
      expect(screen.getByText("ENQ-2026-00000001")).toBeInTheDocument();
    });

    // Click first enquiry
    const rowBtn = screen.getByText("ENQ-2026-00000001").closest("button");
    expect(rowBtn).not.toBeNull();
    fireEvent.click(rowBtn!);

    // Detail panel should render with accessibility attributes and loaded controls
    await waitFor(() => {
      const detail = document.querySelector(".staff-enquiry-detail");
      expect(detail).not.toBeNull();
      expect(detail?.getAttribute("role")).toBe("region");
      expect(detail?.getAttribute("aria-label")).toBe("Enquiry details");
      expect(detail?.getAttribute("tabindex")).toBe("0");
      expect(screen.getByLabelText("Status")).toBeInTheDocument();
    });

    // Verify all management controls are accessible in the detail panel
    expect(screen.getByLabelText("Assign Staff")).toBeInTheDocument();
    expect(screen.getByLabelText("Follow-up Due Date")).toBeInTheDocument();
    expect(screen.getByLabelText(/Add Private Note/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save Follow-Up Update" })).toBeInTheDocument();

    // Verify list card is still rendered alongside detail (desktop two-column grid)
    const listCard = document.querySelector(".staff-enquiry-list-card");
    expect(listCard).not.toBeNull();
    expect(listCard).toHaveClass("lg:col-span-7");

    const detailPanel = document.querySelector(".staff-enquiry-detail");
    expect(detailPanel).toHaveClass("lg:col-span-5");
  });

  it("calculates viewport-aware height on desktop (>=1024px) and resets on mobile", async () => {
    render(<StaffConsole defaultTab="enquiries" />);

    await waitFor(() => {
      expect(screen.getByText("Traveller Enquiries (2)")).toBeInTheDocument();
    });

    const workspace = document.querySelector(".staff-enquiry-workspace") as HTMLElement;
    expect(workspace).not.toBeNull();

    // Mock bounding rect and innerHeight for desktop 1440x900
    vi.spyOn(workspace, "getBoundingClientRect").mockReturnValue({
      top: 220,
      bottom: 876,
      left: 32,
      right: 1408,
      width: 1376,
      height: 656,
      x: 32,
      y: 220,
      toJSON: () => {},
    });

    Object.defineProperty(window, "innerWidth", { writable: true, configurable: true, value: 1440 });
    Object.defineProperty(window, "innerHeight", { writable: true, configurable: true, value: 900 });

    // Trigger window resize
    fireEvent(window, new Event("resize"));

    await waitFor(() => {
      // 900 - 220 - 24 = 656px
      const style = workspace.style.getPropertyValue("--staff-workspace-height");
      expect(style).toBe("656px");
    });

    // Switch to mobile viewport (390px)
    Object.defineProperty(window, "innerWidth", { writable: true, configurable: true, value: 390 });
    Object.defineProperty(window, "innerHeight", { writable: true, configurable: true, value: 844 });

    fireEvent(window, new Event("resize"));

    await waitFor(() => {
      const style = workspace.style.getPropertyValue("--staff-workspace-height");
      expect(style).toBe("");
    });
  });

  it("manages mobile view switching with data-mobile-view attribute and Back button", async () => {
    render(<StaffConsole defaultTab="enquiries" />);

    await waitFor(() => {
      expect(screen.getByText("ENQ-2026-00000001")).toBeInTheDocument();
    });

    const workspace = document.querySelector(".staff-enquiry-workspace");
    // Initially no enquiry selected -> mobile view is "list"
    expect(workspace?.getAttribute("data-mobile-view")).toBe("list");

    // Click an enquiry row
    const rowBtn = screen.getByText("ENQ-2026-00000001").closest("button");
    fireEvent.click(rowBtn!);

    // When enquiry is selected -> mobile view is "detail"
    await waitFor(() => {
      expect(workspace?.getAttribute("data-mobile-view")).toBe("detail");
    });

    // Back button exists
    const backBtn = screen.getByRole("button", { name: "← Back to enquiries" });
    expect(backBtn).toBeInTheDocument();
    expect(backBtn).toHaveClass("staff-enquiry-back");

    // Click back button
    fireEvent.click(backBtn);

    // Workspace returns to "list" view
    await waitFor(() => {
      expect(workspace?.getAttribute("data-mobile-view")).toBe("list");
      expect(document.querySelector(".staff-enquiry-detail")).toBeNull();
    });
  });
});

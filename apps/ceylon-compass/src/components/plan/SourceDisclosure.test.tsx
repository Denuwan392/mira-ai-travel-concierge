import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SourceDisclosure, getSourceDisplayName } from "./SourceDisclosure";
import * as service from "@/lib/live/service";

describe("SourceDisclosure & getSourceDisplayName", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("getSourceDisplayName", () => {
    it("returns explicit label when provided, never exposing internal ID", () => {
      expect(getSourceDisplayName("T01", "Sigiriya Day Tour", "Tour details")).toBe("Tour details");
    });

    it("returns formatted source title when title is provided", () => {
      expect(getSourceDisplayName("T01", "Sigiriya and Minneriya Day Tour from Kandy")).toBe(
        "Source: Sigiriya and Minneriya Day Tour from Kandy",
      );
    });

    it("returns safe fallback when no title or label is provided", () => {
      expect(getSourceDisplayName("T01", undefined, undefined)).toBe("Tour details");
      expect(getSourceDisplayName("P02", "", "")).toBe("Tour details");
    });

    it("never includes the internal ID in the returned display name", () => {
      const label1 = getSourceDisplayName("T01", "Sigiriya Tour");
      const label2 = getSourceDisplayName("T01", undefined, "Tour details");
      const label3 = getSourceDisplayName("T01", undefined, undefined);

      expect(label1).not.toContain("T01");
      expect(label2).not.toContain("T01");
      expect(label3).not.toContain("T01");
    });
  });

  describe("SourceDisclosure component", () => {
    it("renders default 'Tour details' label for selected tour card without exposing T01", () => {
      const { container } = render(
        <SourceDisclosure
          id="T01"
          title="Sigiriya and Minneriya Day Tour from Kandy"
          label="Tour details"
        />,
      );

      const summary = container.querySelector("summary");
      expect(summary?.textContent).toBe("Tour details");
      expect(summary?.textContent).not.toContain("T01");
      expect(summary?.textContent).not.toContain("Published source");

      // Internal ID is kept on data attribute for debugging/auditing
      const details = container.querySelector("details");
      expect(details?.getAttribute("data-source-id")).toBe("T01");
    });

    it("renders provenance label with title when label is not overridden", () => {
      const { container } = render(
        <SourceDisclosure id="D01" title="Sigiriya Fortress" />,
      );

      const summary = container.querySelector("summary");
      expect(summary?.textContent).toBe("Source: Sigiriya Fortress");
      expect(summary?.textContent).not.toContain("D01");
    });

    it("fetches source on expand and renders markdown without duplicate leading H1", async () => {
      const mockApi = vi.spyOn(service, "api").mockResolvedValueOnce({
        title: "Sigiriya and Minneriya Day Tour from Kandy",
        body: "# Sigiriya and Minneriya Day Tour from Kandy\n\n## Highlights\n- Frescoes\n- Safari",
        id: "T01",
        source: "tours/sigiriya.md",
        status: "published",
      });

      const { container } = render(
        <SourceDisclosure
          id="T01"
          title="Sigiriya and Minneriya Day Tour from Kandy"
          label="Tour details"
          stripLeadingH1={true}
        />,
      );

      const details = container.querySelector("details");
      expect(details).toBeInTheDocument();

      // Toggle open
      details!.open = true;
      fireEvent(details!, new Event("toggle"));

      await waitFor(() => {
        expect(mockApi).toHaveBeenCalledWith("/sources/T01");
      });

      await waitFor(() => {
        expect(screen.getByRole("heading", { level: 2, name: "Highlights" })).toBeInTheDocument();
      });

      // Leading H1 was stripped
      expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
      expect(screen.getByText("Frescoes")).toBeInTheDocument();
    });

    it("displays friendly message if source fetching fails", async () => {
      vi.spyOn(service, "api").mockRejectedValueOnce(new Error("Network error"));

      const { container } = render(<SourceDisclosure id="T99" label="Tour details" />);
      const details = container.querySelector("details");

      details!.open = true;
      fireEvent(details!, new Event("toggle"));

      await waitFor(() => {
        expect(screen.getByText("Details unavailable at this time.")).toBeInTheDocument();
      });
    });
  });
});

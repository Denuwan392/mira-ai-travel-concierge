import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MarkdownContent } from "./MarkdownContent";

describe("MarkdownContent", () => {
  it("renders headings as actual semantic HTML headings", () => {
    const markdown = "## Highlights\n### Sub-heading\n#### Detailed note";
    render(<MarkdownContent content={markdown} />);

    const h2 = screen.getByRole("heading", { level: 2, name: "Highlights" });
    const h3 = screen.getByRole("heading", { level: 3, name: "Sub-heading" });
    const h4 = screen.getByRole("heading", { level: 4, name: "Detailed note" });

    expect(h2).toBeInTheDocument();
    expect(h3).toBeInTheDocument();
    expect(h4).toBeInTheDocument();
  });

  it("renders bullet lists and numbered lists correctly", () => {
    const markdown = "- Frescoes\n- Safari jeep\n- Village lunch\n\n1. First step\n2. Second step";
    const { container } = render(<MarkdownContent content={markdown} />);

    const uls = container.querySelectorAll("ul");
    expect(uls.length).toBe(1);
    const lis = uls[0]?.querySelectorAll("li");
    expect(lis?.length).toBe(3);
    expect(lis?.[0]?.textContent).toContain("Frescoes");
    expect(lis?.[1]?.textContent).toContain("Safari jeep");

    const ols = container.querySelectorAll("ol");
    expect(ols.length).toBe(1);
    const olLis = ols[0]?.querySelectorAll("li");
    expect(olLis?.length).toBe(2);
    expect(olLis?.[0]?.textContent).toContain("First step");
  });

  it("renders bold and italic formatting with strong and em tags", () => {
    const markdown = "This has **bold text** and *italic text*.";
    const { container } = render(<MarkdownContent content={markdown} />);

    const strong = container.querySelector("strong");
    expect(strong).toBeInTheDocument();
    expect(strong?.textContent).toBe("bold text");

    const em = container.querySelector("em");
    expect(em).toBeInTheDocument();
    expect(em?.textContent).toBe("italic text");
  });

  it("blocks unsafe HTML tags and script execution", () => {
    const malicious = 'Test text <script>alert("xss")</script> <img src="x" onerror="alert(1)" />';
    const { container } = render(<MarkdownContent content={malicious} />);

    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    // Raw HTML was neutralized and rendered as escaped plain text
    expect(container.textContent).toContain('<script>alert("xss")</script>');
  });

  it("rejects unsafe link protocols like javascript: and permits safe protocols", () => {
    const markdown = "[Safe Link](https://ceyloncompass.com/terms) and [Unsafe Link](javascript:alert(1))";
    const { container } = render(<MarkdownContent content={markdown} />);

    const links = container.querySelectorAll("a");
    expect(links.length).toBe(1);
    expect(links[0]?.getAttribute("href")).toBe("https://ceyloncompass.com/terms");
    expect(links[0]?.textContent).toBe("Safe Link");

    // Unsafe link is not rendered as an anchor tag with javascript: href
    const unsafeLink = container.querySelector('a[href^="javascript:"]');
    expect(unsafeLink).toBeNull();
    expect(container.textContent).toContain("Unsafe Link");
  });

  it("strips leading H1 when stripLeadingH1 is true", () => {
    const markdown = "# Sigiriya and Minneriya Day Tour from Kandy\n\n## Highlights\n- Frescoes";
    render(
      <MarkdownContent
        content={markdown}
        stripLeadingH1={true}
        parentTitle="Sigiriya and Minneriya Day Tour from Kandy"
      />,
    );

    expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
    expect(screen.getByRole("heading", { level: 2, name: "Highlights" })).toBeInTheDocument();
  });

  it("preserves non-leading H1 or H1 when stripLeadingH1 is false", () => {
    const markdown = "# Primary Tour Title\n\nIntro text.";
    render(<MarkdownContent content={markdown} stripLeadingH1={false} />);

    expect(screen.getByRole("heading", { level: 1, name: "Primary Tour Title" })).toBeInTheDocument();
  });

  it("keeps original source content unchanged and intact", () => {
    const original = "## Inclusions\n- Entrance tickets\n- Private guide";
    const { container } = render(<MarkdownContent content={original} />);
    expect(container.textContent).toContain("Inclusions");
    expect(container.textContent).toContain("Entrance tickets");
    expect(container.textContent).toContain("Private guide");
  });
});

import { useState, useId } from "react";
import { api } from "@/lib/live/service";
import { MarkdownContent } from "./MarkdownContent";

export interface SourceDisclosureProps {
  id: string; // Internal identifier (e.g., "T01", "D01", "P01")
  title?: string | undefined; // Known title (e.g., "Sigiriya and Minneriya Day Tour from Kandy")
  label?: string | undefined; // Explicit disclosure summary label (e.g., "Tour details")
  stripLeadingH1?: boolean | undefined;
  defaultOpen?: boolean | undefined;
  className?: string | undefined;
}

/**
 * Centralized transformer from internal source ID and metadata to traveller-facing display label.
 * Guarantees that internal identifiers (like "T01") are never exposed to travellers in UI labels.
 */
export function getSourceDisplayName(
  _sourceId: string,
  title?: string | null | undefined,
  label?: string | null | undefined,
  fallback = "Tour details",
): string {
  if (label && label.trim()) {
    return label.trim();
  }
  if (title && title.trim()) {
    return `Source: ${title.trim()}`;
  }
  return fallback;
}

export function SourceDisclosure({
  id,
  title,
  label,
  stripLeadingH1 = false,
  defaultOpen = false,
  className = "source-disclosure",
}: SourceDisclosureProps) {
  const [data, setData] = useState<{ title: string; body: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const contentId = useId();

  const displayLabel = getSourceDisplayName(
    id,
    title || data?.title,
    label,
    label || (title ? `Source: ${title}` : "Tour details"),
  );

  const fetchSource = () => {
    if (data || loading) return;
    setLoading(true);
    setError(false);
    api<{ title: string; body: string }>("/sources/" + encodeURIComponent(id))
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  };

  return (
    <details
      className={className}
      data-source-id={id}
      data-source-status={data ? "loaded" : loading ? "loading" : error ? "error" : "idle"}
      open={defaultOpen}
      onToggle={(e) => {
        if (e.currentTarget.open) {
          fetchSource();
        }
      }}
    >
      <summary className="source-summary" aria-controls={contentId}>
        {displayLabel}
      </summary>
      <div id={contentId} className="source-content" role="region" aria-label={displayLabel}>
        {loading && <p className="source-status muted">Loading details…</p>}
        {error && <p className="source-status error">Details unavailable at this time.</p>}
        {data && (
          <MarkdownContent
            content={data.body}
            stripLeadingH1={stripLeadingH1}
            parentTitle={title || data.title}
          />
        )}
      </div>
    </details>
  );
}

"use client";

import type { ButtonHTMLAttributes, AnchorHTMLAttributes } from "react";
import Link from "next/link";

/* ── Types ──────────────────────────────────────────────────── */
type Variant = "primary" | "dark" | "light" | "quiet" | "outline";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  /** If provided, renders an <a> / Next Link instead of a <button>. */
  href?: never;
};

type LinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & {
  variant?: Variant;
  href: string;
};

type ActionProps = ButtonProps | LinkProps;

function classes(variant: Variant, extra = "") {
  return ["lux-action", `action-${variant}`, extra].filter(Boolean).join(" ");
}

/**
 * PremiumActionButton
 * Pill-shaped CTA with warm-toned perimeter rim-light on hover.
 * Uses CSS @property conic-gradient animation (see editorial.css).
 *
 * Variants:
 *   primary — orange base, warm-orange rim
 *   dark    — forest-green base (default), warm teal/champagne rim
 *   light   — ivory surface, forest text
 *   outline — transparent, bordered
 *   quiet   — transparent, no border
 *
 * Keeps "PremiumActionButton" export for backward compatibility.
 */
export function PremiumActionButton(props: ActionProps) {
  const { variant = "dark", className = "", ...rest } = props as ButtonProps & { href?: string };

  if (rest.href) {
    const { href, ...linkRest } = rest as unknown as LinkProps;
    return (
      <Link href={href} className={classes(variant, className)} {...(linkRest as object)} />
    );
  }

  return (
    <button
      className={classes(variant, className)}
      {...(rest as ButtonHTMLAttributes<HTMLButtonElement>)}
    />
  );
}

/**
 * SignatureButton
 * Alias exported for use in editorial layouts where a named variant
 * is preferred over a prop. Wraps PremiumActionButton.
 */
export function SignatureButton(props: ActionProps) {
  return <PremiumActionButton variant="primary" {...props} />;
}

/**
 * BrandMark — MIRA compass-rose logomark
 *
 * Renders a minimal SVG compass with the brand orange & deep-orange
 * dart chevron. Accepts an optional size prop (default 33px).
 * Keep this export stable — referenced by FloatingNav and other layouts.
 */
export function BrandMark({ size = 33 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 36 36"
      fill="none"
      aria-hidden="true"
    >
      {/* Outer ring */}
      <circle
        cx="18" cy="18" r="14.75"
        stroke="currentColor"
        strokeWidth="1.4"
      />

      {/* Cardinal tick marks */}
      <path
        d="M18 1.6v4M18 30.4v4M1.6 18h4m24.8 0h4"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />

      {/* Compass dart — light face */}
      <path
        d="M25 10.6l-4.2 10.2-10.2 4.5 4.6-10.6L25 10.6Z"
        fill="#F26B1D"
      />

      {/* Compass dart — shadow face */}
      <path
        d="m20.8 20.8-10.2 4.5 4.6-10.6 5.6 6.1Z"
        fill="#A43C09"
      />

      {/* Thin decorative inner ring (editorial detail) */}
      <circle
        cx="18" cy="18" r="2.5"
        fill="#FAF9F6"
        stroke="#C5A778"
        strokeWidth=".8"
      />
    </svg>
  );
}

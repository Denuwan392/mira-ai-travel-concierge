export function BrandMark({ size = 33 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 36 36" fill="none" aria-hidden="true">
    <circle cx="18" cy="18" r="14.75" stroke="currentColor" strokeWidth="1.4" />
    <path d="M18 1.6v4M18 30.4v4M1.6 18h4m24.8 0h4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    <path d="M25 10.6l-4.2 10.2-10.2 4.5 4.6-10.6L25 10.6Z" fill="#f26b1d" />
    <path d="m20.8 20.8-10.2 4.5 4.6-10.6 5.6 6.1Z" fill="#a43c09" />
  </svg>;
}

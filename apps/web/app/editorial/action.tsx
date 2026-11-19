import type { ButtonHTMLAttributes } from "react";

type ActionProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "light" | "quiet" | "outline" | "dark";
};

export function PremiumActionButton({ variant = "dark", className = "", ...props }: ActionProps) {
  return <button className={`lux-action action-${variant} ${className}`} {...props} />;
}

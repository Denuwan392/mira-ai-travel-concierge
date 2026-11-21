import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Eyebrow({ children, className }: { children: ReactNode; className?: string | undefined }) {
  return <p className={cn("eyebrow text-muted-foreground", className)}>{children}</p>;
}

export function SectionHeading({
  eyebrow,
  title,
  italic,
  className,
  tone = "light",
}: {
  eyebrow: string;
  title: ReactNode;
  italic?: ReactNode;
  className?: string;
  tone?: "light" | "dark";
}) {
  return (
    <div className={className}>
      <Eyebrow className={tone === "dark" ? "text-on-dark-muted" : undefined}>{eyebrow}</Eyebrow>
      <h2 className="display-xl mt-4">
        {title}
        {italic && (
          <>
            {" "}
            <span className="serif-italic font-normal">{italic}</span>
          </>
        )}
      </h2>
    </div>
  );
}

import type { HTMLAttributes } from "react";

export default function Card({
  className = "",
  ...props
}: HTMLAttributes<HTMLElement>) {
  return (
    <article
      className={`border-border bg-surface text-foreground rounded-2xl border p-5 shadow-sm ${className}`}
      {...props}
    />
  );
}

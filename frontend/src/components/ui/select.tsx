import { ChevronDown } from "lucide-react";
import type { SelectHTMLAttributes } from "react";

export default function Select({
  className = "",
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div className="relative">
      <select
        className={`border-control-border bg-background text-foreground focus-visible:border-focus focus-visible:ring-focus min-h-11 w-full appearance-none rounded-xl border px-3.5 py-2.5 pr-10 text-sm transition-colors focus-visible:ring-2 focus-visible:outline-none ${className}`}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        aria-hidden="true"
        className="text-muted-foreground pointer-events-none absolute top-1/2 right-3.5 size-4 -translate-y-1/2"
      />
    </div>
  );
}

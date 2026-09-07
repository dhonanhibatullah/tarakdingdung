import {
  Circle,
  CircleCheck,
  CircleX,
  Info,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";

export type StatusVariant =
  | "success"
  | "warning"
  | "critical"
  | "info"
  | "neutral";

interface StatusBadgeProps {
  variant: StatusVariant;
  children: ReactNode;
}

const STATUS_ICON = {
  success: CircleCheck,
  warning: TriangleAlert,
  critical: CircleX,
  info: Info,
  neutral: Circle,
} satisfies Record<StatusVariant, LucideIcon>;

const VARIANT_CLASSES: Record<StatusVariant, string> = {
  success: "border-success/30 bg-background text-success",
  warning: "border-warning/30 bg-background text-warning",
  critical: "border-critical/30 bg-background text-critical",
  info: "border-info/30 bg-background text-info",
  neutral: "border-border bg-background text-foreground",
};

export default function StatusBadge({ variant, children }: StatusBadgeProps) {
  const Icon = STATUS_ICON[variant];

  return (
    <span
      data-variant={variant}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${VARIANT_CLASSES[variant]}`}
    >
      <Icon aria-hidden="true" className="size-3.5" />
      {children}
    </span>
  );
}

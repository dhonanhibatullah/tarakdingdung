import Link from "next/link";
import { ArrowUpRight, type LucideIcon } from "lucide-react";

import StatusBadge, { type StatusVariant } from "@/components/ui/status-badge";

interface MetricCardProps {
  label: string;
  value: string;
  description: string;
  href: string;
  icon: LucideIcon;
  status?: string;
  statusVariant?: StatusVariant;
}

export default function MetricCard({
  label,
  value,
  description,
  href,
  icon: Icon,
  status,
  statusVariant = "neutral",
}: MetricCardProps) {
  return (
    <Link
      href={href}
      className="border-border bg-surface focus-visible:ring-focus focus-visible:ring-offset-background group flex min-h-48 flex-col justify-between rounded-2xl border p-5 shadow-sm transition-[transform,box-shadow] hover:-translate-y-0.5 hover:shadow-md focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
      aria-label={`${label}: ${value}. ${description}`}
    >
      <div className="flex items-start justify-between gap-3">
        <span className="bg-background text-primary flex size-11 items-center justify-center rounded-xl">
          <Icon aria-hidden="true" className="size-5" />
        </span>
        {status ? (
          <StatusBadge variant={statusVariant}>{status}</StatusBadge>
        ) : null}
      </div>
      <div className="mt-6">
        <p className="font-display text-primary text-4xl tracking-wide">
          {value}
        </p>
        <div className="mt-2 flex items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold">{label}</h3>
            <p className="text-muted-foreground mt-1 text-xs">{description}</p>
          </div>
          <ArrowUpRight
            aria-hidden="true"
            className="text-primary size-5 shrink-0 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
          />
        </div>
      </div>
    </Link>
  );
}

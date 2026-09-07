import type { ReactNode } from "react";

import Card from "@/components/ui/card";

interface ResourceCardProps {
  title: string;
  summary?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}

export default function ResourceCard({
  title,
  summary,
  actions,
  children,
}: ResourceCardProps) {
  return (
    <Card className="flex h-full flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="font-display text-primary text-xl tracking-wide [overflow-wrap:anywhere]">
            {title}
          </h2>
          {summary ? <div className="mt-1.5">{summary}</div> : null}
        </div>
        {actions ? <div className="shrink-0">{actions}</div> : null}
      </div>
      <div className="text-sm leading-6">{children}</div>
    </Card>
  );
}

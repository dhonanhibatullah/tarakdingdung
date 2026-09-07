import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
}

export default function PageHeader({
  title,
  description,
  actions,
}: PageHeaderProps) {
  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 className="font-display text-primary text-3xl tracking-wide sm:text-4xl">
          {title}
        </h1>
        {description ? (
          <p className="text-foreground/70 mt-2 max-w-2xl text-sm sm:text-base">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div className="w-full shrink-0 sm:w-auto">{actions}</div>
      ) : null}
    </header>
  );
}

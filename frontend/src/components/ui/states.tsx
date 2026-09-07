import type { ReactNode } from "react";

interface StateProps {
  title: string;
  description: string;
  action?: ReactNode;
}

function State({ title, description, action }: StateProps) {
  return (
    <section className="border-border bg-muted rounded-2xl border border-dashed p-6 text-center">
      <h2 className="font-display text-foreground text-lg tracking-wide">
        {title}
      </h2>
      <p className="text-foreground/70 mt-2 text-sm">{description}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </section>
  );
}

export function EmptyState(props: StateProps) {
  return <State {...props} />;
}

export function ErrorState(props: StateProps) {
  return <State {...props} />;
}

export function LoadingState({ title = "Loading" }: { title?: string }) {
  return (
    <div
      role="status"
      aria-label={title}
      className="border-border bg-muted animate-pulse rounded-2xl border p-6"
    >
      <div className="bg-foreground/15 h-5 w-32 rounded" />
      <div className="bg-foreground/10 mt-3 h-4 w-2/3 rounded" />
    </div>
  );
}

export default EmptyState;

import type { ReactNode } from "react";
import { ShieldX } from "lucide-react";

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

export function AccessDeniedState({
  action,
  description = "Your account is signed in, but it does not have permission to view this page.",
}: Pick<StateProps, "action"> & { description?: string } = {}) {
  return (
    <section className="border-border bg-muted rounded-2xl border p-6 text-center">
      <ShieldX aria-hidden="true" className="text-critical mx-auto size-10" />
      <h1 className="font-display text-foreground mt-3 text-2xl tracking-wide">
        Access denied
      </h1>
      <p className="text-foreground/70 mx-auto mt-2 max-w-lg text-sm">
        {description}
      </p>
      {action ? <div className="mt-5">{action}</div> : null}
    </section>
  );
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

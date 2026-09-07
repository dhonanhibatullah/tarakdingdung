import Link from "next/link";

import LogoutButton from "@/components/layout/LogoutButton";
import { AccessDeniedState } from "@/components/ui/states";

interface AccessDeniedProps {
  description?: string;
}

export default function AccessDenied({ description }: AccessDeniedProps = {}) {
  return (
    <AccessDeniedState
      description={
        description ??
        "Your account is signed in, but it does not have permission to view this page."
      }
      action={
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/dashboard"
            className="bg-primary text-surface focus-visible:ring-focus focus-visible:ring-offset-background inline-flex min-h-11 items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold transition-opacity hover:opacity-90 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
          >
            Return to dashboard
          </Link>
          <LogoutButton />
        </div>
      }
    />
  );
}

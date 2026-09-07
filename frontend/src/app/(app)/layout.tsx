import type { ReactNode } from "react";

import AppShell from "@/components/layout/AppShell";
import { requireSessionContext } from "@/lib/session";

export default async function AppLayout({
  children,
}: {
  children: ReactNode;
}) {
  const session = await requireSessionContext();
  return (
    <AppShell user={session.user} permissions={[...session.permissions]}>
      {children}
    </AppShell>
  );
}

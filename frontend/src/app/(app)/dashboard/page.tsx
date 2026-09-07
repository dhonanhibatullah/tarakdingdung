import type { Metadata } from "next";
import { Coins, TrendingUp, Wallet, Workflow } from "lucide-react";

import PageHeader from "@/components/ui/page-header";

import MetricCard from "./_components/MetricCard";
import RecentCycles from "./_components/RecentCycles";

export const metadata: Metadata = {
  title: "Overview — Tarakdingdung",
  description: "Engine status, strategy health, and portfolio at a glance.",
};

export default function DashboardPage() {
  return (
    <main className="mx-auto w-full max-w-7xl space-y-8 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Overview"
        description="Engine status, strategy health, and portfolio at a glance."
      />

      <p
        className="border-accent bg-highlight/20 text-foreground rounded-xl border px-4 py-3 text-sm font-semibold"
        role="note"
      >
        Sample data. Connect the engine API to show live figures.
      </p>

      <section aria-labelledby="health-heading">
        <div>
          <h2
            id="health-heading"
            className="font-display text-primary text-2xl tracking-wide"
          >
            Trading health
          </h2>
          <p className="text-muted-foreground mt-1 text-sm">
            Figures cover every enabled strategy across all venues.
          </p>
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Active strategies"
            value="3"
            description="Enabled and stepping each cycle"
            href="/strategies"
            icon={Workflow}
            status="Running"
            statusVariant="success"
          />
          <MetricCard
            label="Portfolio equity"
            value="Rp 41.2M"
            description="Cash plus marked positions"
            href="/portfolio"
            icon={Wallet}
            status="+1.8% · 24h"
            statusVariant="success"
          />
          <MetricCard
            label="Open positions"
            value="5"
            description="Held across Indodax and Tokocrypto"
            href="/portfolio"
            icon={Coins}
            status="2 venues"
            statusVariant="info"
          />
          <MetricCard
            label="Halted strategies"
            value="1"
            description="Stopped by a risk rule, awaiting review"
            href="/strategies"
            icon={TrendingUp}
            status="Needs review"
            statusVariant="critical"
          />
        </div>
      </section>

      <RecentCycles />
    </main>
  );
}

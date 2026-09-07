import PageHeader from "@/components/ui/page-header";
import { LoadingState } from "@/components/ui/states";

const CARDS = ["Active strategies", "Portfolio equity", "Open positions", "Halted strategies"] as const;

export default function Loading() {
  return (
    <main className="mx-auto w-full max-w-7xl space-y-8 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader title="Overview" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {CARDS.map((label) => (
          <LoadingState key={label} title={`Loading ${label}`} />
        ))}
      </div>
    </main>
  );
}

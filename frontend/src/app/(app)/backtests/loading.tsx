import PageHeader from "@/components/ui/page-header";
import { LoadingState } from "@/components/ui/states";

export default function Loading() {
  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Backtests"
        description="Replay a strategy over stored history."
      />
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <LoadingState key={i} title="Loading backtests" />
        ))}
      </div>
    </main>
  );
}

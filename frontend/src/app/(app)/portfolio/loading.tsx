import PageHeader from "@/components/ui/page-header";
import { LoadingState } from "@/components/ui/states";

export default function Loading() {
  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Portfolio"
        description="Holdings and equity across every venue."
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <LoadingState key={i} title="Loading portfolio" />
        ))}
      </div>
      <LoadingState title="Loading equity curve" />
    </main>
  );
}

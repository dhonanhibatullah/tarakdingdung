import PageHeader from "@/components/ui/page-header";
import { LoadingState } from "@/components/ui/states";

export default function Loading() {
  return (
    <main className="mx-auto w-full max-w-4xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="Validations"
        description="Walk-forward search with an overfitting gate."
      />
      <LoadingState title="Loading validations" />
    </main>
  );
}

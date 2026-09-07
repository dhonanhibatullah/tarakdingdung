import PageHeader from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/states";

interface PlaceholderPageProps {
  title: string;
  description: string;
  comingSoon: string;
}

export default function PlaceholderPage({
  title,
  description,
  comingSoon,
}: PlaceholderPageProps) {
  return (
    <main className="mx-auto w-full max-w-7xl space-y-8 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader title={title} description={description} />
      <EmptyState title="Nothing here yet" description={comingSoon} />
    </main>
  );
}

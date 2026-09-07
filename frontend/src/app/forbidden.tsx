import AccessDenied from "@/components/layout/AccessDenied";

export default function Forbidden() {
  return (
    <main className="bg-background flex min-h-screen items-center justify-center px-4 py-8">
      <div className="w-full max-w-2xl">
        <AccessDenied />
      </div>
    </main>
  );
}

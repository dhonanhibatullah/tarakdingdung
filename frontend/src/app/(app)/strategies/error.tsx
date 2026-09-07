"use client";

import { useEffect } from "react";

import Button from "@/components/ui/button";
import PageHeader from "@/components/ui/page-header";
import { ErrorState } from "@/components/ui/states";

export default function StrategiesError({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader title="Strategies" />
      <ErrorState
        title="Could not load strategies"
        description="The backend did not respond as expected. Check that it is running and reachable."
        action={
          <Button type="button" onClick={reset}>
            Try again
          </Button>
        }
      />
    </main>
  );
}

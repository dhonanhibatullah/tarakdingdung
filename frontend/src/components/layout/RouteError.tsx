"use client";

import { useEffect } from "react";

import Button from "@/components/ui/button";
import PageHeader from "@/components/ui/page-header";
import { ErrorState } from "@/components/ui/states";

interface RouteErrorProps {
  title: string;
  error: Error;
  reset: () => void;
  description?: string;
}

/** Shared body for a route segment's error.tsx. */
export default function RouteError({
  title,
  error,
  reset,
  description = "The backend did not respond as expected. Check that it is running and reachable.",
}: RouteErrorProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader title={title} />
      <ErrorState
        title={`Could not load ${title.toLowerCase()}`}
        description={description}
        action={
          <Button type="button" onClick={reset}>
            Try again
          </Button>
        }
      />
    </main>
  );
}

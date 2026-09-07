"use client";

import RouteError from "@/components/layout/RouteError";

export default function Error(props: { error: Error; reset: () => void }) {
  return <RouteError title="Validations" {...props} />;
}

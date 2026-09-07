import "server-only";

import { apiFetch, buildQuery } from "@/lib/api/client";
import type { SymbolRef } from "@/lib/api/strategies";

// Mirrors CoverageResponse in response.py. Windows are epoch milliseconds.

export interface CoverageGap {
  start: number;
  end: number;
}

export interface CoverageResponse {
  symbol: SymbolRef;
  interval: string;
  expected: number;
  present: number;
  completeness: number;
  gaps: CoverageGap[];
}

export interface CoverageQuery {
  venue: string;
  base: string;
  quote: string;
  window_start: number;
  window_end: number;
  interval: string;
}

export async function getCoverage(
  query: CoverageQuery,
): Promise<CoverageResponse> {
  return apiFetch(`/trading/coverage${buildQuery(query)}`);
}

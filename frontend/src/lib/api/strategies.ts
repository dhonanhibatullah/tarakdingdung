import "server-only";

import { apiFetch, buildQuery } from "@/lib/api/client";
import type {
  AuditFields,
  IdResponse,
  PageDataResponse,
  PageQuery,
} from "@/lib/api/types";

export type StrategyMode = "PAPER" | "LIVE";

export interface SymbolRef {
  venue: string;
  base: string;
  quote: string;
}

export interface StrategyResponse extends AuditFields {
  id: string;
  name: string;
  description: string;
  kind: string;
  mode: StrategyMode;
  universe: SymbolRef[];
  parameters: Record<string, unknown>;
  is_enabled: boolean;
  preferences: Record<string, unknown>;
}

export interface CreateStrategyRequest {
  name: string;
  kind: string;
  mode: StrategyMode;
  universe: SymbolRef[];
  description?: string;
  parameters?: Record<string, unknown>;
  is_enabled?: boolean;
}

export interface UpdateStrategyRequest {
  name?: string;
  description?: string;
  kind?: string;
  mode?: StrategyMode;
  universe?: SymbolRef[];
  parameters?: Record<string, unknown>;
  is_enabled?: boolean;
}

export interface ListStrategiesQuery extends PageQuery {
  mode?: StrategyMode;
}

/** POST /engine/{id}/dry-run — CycleResponse in response.py. */
export interface CycleResponse {
  timestamp: number;
  strategy_id: string;
  decision: string;
  halted_by?: string | null;
  orders: number;
  rejected: number;
  reconciled: number;
}

export async function listStrategies(
  query: ListStrategiesQuery = {},
): Promise<PageDataResponse<StrategyResponse>> {
  return apiFetch(`/trading/strategies${buildQuery(query)}`);
}

export async function getStrategy(id: string): Promise<StrategyResponse> {
  return apiFetch(`/trading/strategies/${id}`);
}

export async function createStrategy(
  request: CreateStrategyRequest,
): Promise<IdResponse> {
  return apiFetch("/trading/strategies", { method: "POST", body: request });
}

export async function updateStrategy(
  id: string,
  request: UpdateStrategyRequest,
): Promise<void> {
  return apiFetch(`/trading/strategies/${id}`, {
    method: "PATCH",
    body: request,
  });
}

export async function deleteStrategy(id: string): Promise<void> {
  return apiFetch(`/trading/strategies/${id}`, { method: "DELETE" });
}

export async function dryRunStrategy(id: string): Promise<CycleResponse> {
  return apiFetch(`/trading/engine/${id}/dry-run`, {
    method: "POST",
    body: {},
  });
}

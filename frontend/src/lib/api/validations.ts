import "server-only";

import { apiFetch } from "@/lib/api/client";

// Mirrors ValidationRunResponse / OverfittingResponse in response.py. The
// backend has no list endpoint — a run is created and then fetched by id.

export interface OverfittingResponse {
  probability: number;
  threshold: number;
  passed: boolean;
}

export interface ValidationRunResponse {
  id: string;
  strategy_id: string;
  window_start: number;
  window_end: number;
  trials: number;
  overfitting: OverfittingResponse;
  created_at: string;
}

export interface RunValidationRequest {
  strategy_id: string;
  window_start: number;
  window_end: number;
  initial_equity: string;
  parameter_grid: Record<string, unknown>[];
  interval?: string;
  subsets?: number;
  threshold?: number;
}

export async function runValidation(
  request: RunValidationRequest,
): Promise<ValidationRunResponse> {
  return apiFetch("/trading/validations", { method: "POST", body: request });
}

export async function getValidation(
  id: string,
): Promise<ValidationRunResponse> {
  return apiFetch(`/trading/validations/${id}`);
}

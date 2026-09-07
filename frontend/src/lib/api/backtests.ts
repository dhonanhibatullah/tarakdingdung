import "server-only";

import { apiFetch, buildQuery } from "@/lib/api/client";
import type { PageDataResponse, PageQuery } from "@/lib/api/types";

// Mirrors BacktestRunResponse / PerformanceResponse in response.py.

export interface PerformanceResponse {
  total_return: number;
  sharpe: number;
  sortino: number;
  max_drawdown: number;
  turnover: number;
  gross_return: number;
  net_return: number;
  cost_drag: number;
  trade_count: number;
}

export interface BacktestRunResponse {
  id: string;
  strategy_id: string;
  window_start: number;
  window_end: number;
  initial_equity: string;
  report: PerformanceResponse;
  created_at: string;
}

export interface ListBacktestsQuery extends PageQuery {
  strategy_id?: string;
}

export interface RunBacktestRequest {
  strategy_id: string;
  window_start: number;
  window_end: number;
  initial_equity: string;
  interval?: string;
  periods_per_year?: number;
  min_completeness?: number;
}

export async function listBacktests(
  query: ListBacktestsQuery = {},
): Promise<PageDataResponse<BacktestRunResponse>> {
  return apiFetch(`/trading/backtests${buildQuery(query)}`);
}

export async function getBacktest(id: string): Promise<BacktestRunResponse> {
  return apiFetch(`/trading/backtests/${id}`);
}

export async function runBacktest(
  request: RunBacktestRequest,
): Promise<BacktestRunResponse> {
  return apiFetch("/trading/backtests", { method: "POST", body: request });
}

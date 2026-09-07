import "server-only";

import { apiFetch, buildQuery } from "@/lib/api/client";
import type { SymbolRef } from "@/lib/api/strategies";

// Mirrors CurrentPortfolioResponse / EquityCurveResponse in response.py.
// Money fields cross the wire as decimal strings; keep them as strings and
// format at the edge.

export interface PositionResponse {
  symbol: SymbolRef;
  quantity: string;
  average_price: string;
}

export interface PortfolioResponse {
  timestamp: number;
  cash: Record<string, string>;
  positions: PositionResponse[];
  equity: string;
  /**
   * Per-asset free balance of every reachable venue at the last sync, keyed
   * `{ venue: { asset: amount } }`. Kept whole even under `?venue=` so the page
   * can build its venue switch.
   */
  balances: Record<string, Record<string, string>>;
  /**
   * Per-venue equity (priced positions on the venue plus its IDR balance).
   * Under `?venue=`, `equity` above is that venue's figure; this map still
   * lists every venue.
   */
  equity_by_venue: Record<string, string>;
}

export interface RiskStateResponse {
  timestamp: number;
  equity_peak: string;
  daily_pnl: string;
  realized_volatility: number;
  halted: boolean;
}

export interface CurrentPortfolioResponse {
  portfolio: PortfolioResponse;
  risk_state: RiskStateResponse;
}

export interface EquityPointResponse {
  timestamp: number;
  equity: string;
}

export interface EquityCurveResponse {
  points: EquityPointResponse[];
}

export async function getCurrentPortfolio(
  venue?: string,
): Promise<CurrentPortfolioResponse> {
  return apiFetch(`/trading/portfolio${buildQuery({ venue })}`);
}

export async function getEquityCurve(
  windowStart: number,
  windowEnd: number,
  venue?: string,
): Promise<EquityCurveResponse> {
  return apiFetch(
    `/trading/portfolio/equity${buildQuery({
      window_start: windowStart,
      window_end: windowEnd,
      venue,
    })}`,
  );
}

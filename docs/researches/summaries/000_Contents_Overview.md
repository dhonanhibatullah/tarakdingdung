# Summaries — Contents Overview

Index of every file in `summaries/`. Keep in sync on every add, update, or
retire (see `../AGENTS.md` §5). Numbers are never reused; retired entries stay
here with strikethrough and a reason.

| #   | File | Question answered | Status |
|-----|------|-------------------|--------|
| 001 | `001_Best_Indonesian_Broker_For_Automated_Stock_And_Crypto_Trading.md` | Which Indonesia-accessible broker(s) to use for automated crypto and stock trading — most trustworthy, best API? | draft |
| 002 | `002_Cutting_Edge_High_Performance_Crypto_Trading_Algorithms_And_AI.md` | What are the most cutting-edge / high-performance crypto trading algorithms and AI (DRL, LLM multi-agent, transformers) — what do they really achieve, and what should a v1 engine take from them? | draft |
| 003 | `003_Exchange_REST_API_Endpoint_Inventory.md` | Complete REST endpoint inventory for Indodax v1 "tapi", Indodax v2 (`/api/v2/*`), and Tokocrypto v1 (`/open/v1/*`) — auth model, params, response envelopes, and how they map to the `contracts/api` + `infrastructure/api` classes. | draft |
| 004 | `004_Automated_Trading_Engine_Implementation_Plan.md` | Point-by-point v1 build plan: spot-only strategy (no perp API on either venue), pure `decide()` interface, phased pipeline (collector → backtester → validation/PBO → paper → tiny live), always-on risk overlay, and codebase mapping. | draft |

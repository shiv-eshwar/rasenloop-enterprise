# ADR 0001 — Fintech vertical, Python/Next stack, live+fake Rasen transports

**Status:** Accepted  
**Date:** 2026-11-23  
**Deciders:** Project owner (interview candidate)

## Context

RasenLoop Enterprise must impress Rasen Labs within ~1 week. We need a vertical that stresses money safety, Hinglish, OTP/DTMF, and fraud escalation, plus a stack that can implement MCP, webhooks, SSE, and WebSocket media evals quickly.

## Decision

1. **Domain:** Pan-India fintech / digital bank mock (“BharatPay”), not airline or quick-commerce.
2. **Stack:** Python 3.12 + FastAPI for backend/MCP/eval harness; Next.js + TypeScript for War Room.
3. **Rasen access:** Support **live** API integration and a **Fake/Chaos Transport** for unit tests and offline demos.
4. **Remote:** Public GitHub repo `shiv-eshwar/rasenloop-enterprise` with frequent pushes.

## Consequences

**Positive**

- Refund/idempotency stories are interview-differentiating.
- FastAPI fits MCP + webhooks + SSE proxy in one language as the eval harness.
- Fake transport keeps CI deterministic and demo-resilient.

**Negative**

- Two languages (Python + TS) to maintain.
- Fintech compliance theater must be clearly labeled as a demo, not certification.
- Live eval concurrency constrained by workspace limits.

## Alternatives considered

- Quick-commerce vertical — weaker “money integrity” narrative than ledger refunds.
- Full TypeScript monorepo — fine, but Python preferred for rapid asyncio audio harness and pytest discipline.
- Live-only Rasen (no fake) — too fragile for CI and interview network failure.

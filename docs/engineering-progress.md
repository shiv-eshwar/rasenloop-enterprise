# Engineering Progress — RasenLoop Enterprise

Living log of what was built, verified, and decided. Update this file **every iteration** and at the end of every phase in [plan.md](./plan.md).

**Current phase:** Phase 5 complete (fake/offline path green) — live Rasen optional  
**Interview target window:** week of 2026-11-24  
**Repo:** https://github.com/shiv-eshwar/rasenloop-enterprise

---

## How to use this file

1. Add a new dated entry at the **top** of the “Iteration log” section (newest first).
2. When a phase completes, check it off in the Phase scoreboard below and link the commit SHA.
3. Record live Rasen evidence (`call_id`, `X-Request-Id`, share-link) whenever available.
4. Never delete old entries — append/amend only.

---

## Phase scoreboard

| Phase | Status | Completed | Commit | Notes |
| --- | --- | --- | --- | --- |
| Docs bootstrap (`whatthis`, architecture, engineering, plan, supporting) | **Done** | 2026-11-23 | `2d2be4b` | Spec lock: fintech + FastAPI/Next + live+fake |
| 0 — Monorepo + rasen-client | **Done** | 2026-11-24 | `8cb4d02` | FakeChaosTransport + Idempotency-Key / If-Match |
| 1 — Domain + policy + MCP | **Done** | 2026-11-24 | `8cb4d02` | 5 MCP tools; effect_id UNIQUE; chaos hooks |
| 2 — Pre-call + agent + webhooks | **Done** | 2026-11-24 | `8cb4d02` | GET+POST lookup; Standard Webhooks verify; fake bootstrap |
| 3 — Reconciler + War Room + kill switch | **Done** | 2026-11-24 | `8cb4d02` | Next.js War Room builds; kill switch on fake |
| 4 — Signals + evals + auto-rollback | **Done** | 2026-11-24 | `8cb4d02` | ≥8 scenarios; bad publish → rollback |
| 5 — CI + demo + field report | **Done** | 2026-11-24 | `8cb4d02` | CI workflow; Loom/live metrics still human |
| Interview ready | **Fake-path ready** | 2026-11-24 | `8cb4d02` | Add `RASEN_API_KEY` for live share-link demos |

---

## Iteration log

### 2026-11-24 — Iteration 1: End-to-end Phases 0–5 (fake transport)

- **Goal:** Implement the full plan against docs, green tests, War Room build, push to GitHub.
- **Built:**
  - `packages/rasen-client` — Transport protocol, `FakeChaosTransport`, `LiveHttpTransport`, `RasenClient`
  - `packages/shared` — signal enums + eval schema types
  - `apps/backend` — models, policy, ledger/effects, CRM, reconciler, signals, control plane, pre_call/webhooks/otp/war_room APIs
  - `apps/mcp-server` — REST + minimal JSON-RPC `/mcp` with 5 tools
  - `apps/war-room` — Next.js supervisor UI (calls, kill switch, evals, signals)
  - `apps/eval-harness` — 8+ offline scenarios + runner + auto-rollback inject path
  - `scripts/seed_db.py`, `scripts/bootstrap_rasen_agent.py`
  - `.github/workflows/ci.yml`, Makefile, `.env.example`
- **Tests:** `26 passed` (`make test` / pytest); `ruff check` clean; `npm run build` in War Room OK; `make smoke-eval` blockers pass; fake bootstrap publishes agent + share-link fixture
- **Live Rasen notes:** Not exercised this iteration (no API key in session). Fake path covers create/publish/rollback/kill-switch.
- **Blockers:** None for offline demo. Live needs tunnel + `RASEN_API_KEY`.
- **Next:** Optional live bootstrap; rehearse [demo-playbook.md](./demo-playbook.md); fill field-report with real `call_id`s.

### 2026-11-23 — Iteration 0: Spec & docs bootstrap

- **Goal:** Lock project definition and write best-practice engineering docs before code.
- **Built:**
  - Created local git repo `/Users/shiv/rasenloop-enterprise`
  - Created GitHub remote `shiv-eshwar/rasenloop-enterprise` (retry after initial TLS timeout)
  - Wrote full `/docs` set + README
- **Tests:** N/A (docs only)
- **Live Rasen notes:** Research completed against docs.rasen.ai (API v1.14.0).
- **Next:** Phase 0 implementation (completed in Iteration 1).

---

## Metrics scratchpad (fill during live Phase 5)

| Metric | Value | Source |
| --- | --- | --- |
| Pre-call p95 | _TBD live_ | backend timing logs |
| Tool latency p95 | _TBD live_ | `listAgentToolRuns.latency_ms` |
| Shadow scenarios passing | 8/8 blockers (fake) | `make smoke-eval` |
| Auto-rollbacks triggered in rehearsal | 1 (fake bad publish) | control plane tests |
| Cost per resolved demo ticket | _TBD live_ | `POST /usage/query` |
| Double-refunds under chaos | 0 | ledger/reconciler asserts |

---

## Interview readiness checklist

- [x] Fake end-to-end path green (tests + War Room build + smoke eval)
- [x] Kill switch + auto-rollback demonstrated on fake transport
- [x] Docs + demo playbook present
- [ ] Live share-link call recorded (optional, needs API key)
- [ ] Loom backup of cold demo (human)

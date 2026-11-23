# Engineering Progress — RasenLoop Enterprise

Living log of what was built, verified, and decided. Update this file **every iteration** and at the end of every phase in [plan.md](./plan.md).

**Current phase:** Phase 0 (not started — documentation bootstrap complete)  
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
| 0 — Monorepo + rasen-client | Not started | — | — | |
| 1 — Domain + policy + MCP | Not started | — | — | |
| 2 — Pre-call + agent + webhooks | Not started | — | — | |
| 3 — Reconciler + War Room + kill switch | Not started | — | — | |
| 4 — Signals + evals + auto-rollback | Not started | — | — | |
| 5 — CI + demo + field report | Not started | — | — | |
| Interview ready | Not started | — | — | |

---

## Iteration log

### 2026-11-23 — Iteration 0: Spec & docs bootstrap

- **Goal:** Lock project definition and write best-practice engineering docs before code.
- **Built:**
  - Created local git repo `/Users/shiv/rasenloop-enterprise`
  - Created GitHub remote `shiv-eshwar/rasenloop-enterprise` (retry after initial TLS timeout)
  - Wrote:
    - `docs/whatthis.md`
    - `docs/architecture.md`
    - `docs/engineering.md`
    - `docs/plan.md`
    - `docs/engineering-progress.md` (this file)
    - `docs/api-contracts.md`
    - `docs/evals-and-chaos.md`
    - `docs/security-and-runbook.md`
    - `docs/demo-playbook.md`
    - `docs/field-report-template.md`
    - `docs/decisions/0001-fintech-vertical-and-stack.md`
    - `README.md`
- **Tests:** N/A (docs only)
- **Live Rasen notes:** Research completed against docs.rasen.ai (API v1.14.0, Nov 14 2026 changelog). No production calls yet.
- **Blockers:** None for docs. Implementation awaits Phase 0.
- **Decisions locked:**
  - Vertical = pan-India fintech / digital bank (BharatPay mock)
  - Stack = Python FastAPI + Next.js War Room
  - Access = live Rasen API + Fake/Chaos Transport
  - Push every meaningful commit to `shiv-eshwar` GitHub
- **Next:** Phase 0 — monorepo tooling, `packages/rasen-client` with FakeChaosTransport, Makefile, first green `make test`.

---

## Metrics scratchpad (fill during Phase 4–5)

| Metric | Value | Source |
| --- | --- | --- |
| Pre-call p95 | _TBD_ | backend timing logs |
| Tool latency p95 | _TBD_ | `listAgentToolRuns.latency_ms` |
| Shadow scenarios passing | _TBD_ | eval report |
| Auto-rollbacks triggered in rehearsal | _TBD_ | control plane |
| Cost per resolved demo ticket | _TBD_ | `POST /usage/query` |
| Double-refunds under chaos | _TBD_ | ledger asserts (must stay 0) |

---

## Known issues / debt

| ID | Issue | Severity | Plan |
| --- | --- | --- | --- |
| D0 | `pre_call` does not run on browser test calls | Medium | Document in demo; show pre_call via phone or integration test |
| D1 | Transfer E.164 placeholders may not be real carrier numbers | Low | Demo spoken handoff + tool intent; wire numbers if available |
| D2 | Workspace concurrency default ~3 | Medium | Serial eval runs; respect Retry-After |

---

## Sign-off checklist (interview day)

- [ ] Phase 0–4 complete or explicitly waived with fallback demo path
- [ ] `make test` green
- [ ] Live share-link works OR Loom covers voice UX
- [ ] War Room screenshot/GIF in README or demo doc
- [ ] Field report draft reviewed once aloud
- [ ] Kill switch + rollback rehearsed once

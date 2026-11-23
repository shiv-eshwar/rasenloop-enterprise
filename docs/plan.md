# RasenLoop Enterprise — Implementation Plan

> **For agentic workers:** Execute phase-by-phase. Prefer FakeChaosTransport tests with every money/idempotency change. Update `docs/engineering-progress.md` at the end of each phase. Push to `origin` after each phase commit.

**Goal:** Ship an interview-ready self-healing fintech voice support system on Rasen API v1.14.0 with pre_call hydration, policy MCP tools, indeterminate reconciliation, War Room, living evals, and auto-rollback.

**Architecture:** FastAPI backend + Streamable HTTP MCP server + Next.js War Room + Python eval harness, all talking to Rasen through `packages/rasen-client` (live + fake transports). See [architecture.md](./architecture.md).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Pydantic v2, httpx, Next.js/React/TS, Rasen Developer API, SQLite (Postgres-ready).

## Global Constraints

- Rasen base URL: `https://api.rasen.ai/v1`
- Never put `RASEN_API_KEY` in browser or mobile code
- Every mutation: new persisted `Idempotency-Key`; retries use the same key
- Draft/tool/publish writes: `If-Match` draft ETag; refresh on `draft_conflict`
- `indeterminate` tool outcomes: reconcile only — never blind retry
- Fintech vertical only (BharatPay mock bank)
- Unit tests default to `RASEN_TRANSPORT=fake`
- Docs in `/docs` stay authoritative; progress logged every phase
- Repo: `github.com/shiv-eshwar/rasenloop-enterprise`

---

## Phase map (interview week)

| Phase | Name | Demo value | Est. |
| --- | --- | --- | --- |
| 0 | Repo bootstrap + rasen-client skeleton | Foundation | 0.5 day |
| 1 | Domain DB + policy engine + MCP tools | Money-safe tools | 1 day |
| 2 | Pre-call + Rasen agent bootstrap + webhooks | Live voice path | 1 day |
| 3 | Reconciler + War Room MVP + kill switch | Ops wow | 1 day |
| 4 | Signals + eval harness + auto-rollback | Thesis wow | 1–1.5 days |
| 5 | Polish, demo playbook, field report, CI | Interview harden | 0.5–1 day |

Stretch (only if Phase 0–4 green): campaigns, SIP, richer audio synthesis.

---

## File map (create over phases)

```text
apps/backend/
  app/main.py
  app/settings.py
  app/db.py
  app/models.py
  app/policy.py
  app/services/crm.py
  app/services/ledger.py
  app/services/effects.py
  app/services/reconciler.py
  app/services/signals.py
  app/services/control_plane.py
  app/api/pre_call.py
  app/api/webhooks.py
  app/api/war_room.py
  app/api/otp.py
  tests/...
apps/mcp-server/
  app/main.py
  app/tools.py
  tests/...
apps/war-room/
  app/...
apps/eval-harness/
  rasenloop_eval/scenarios.py
  rasenloop_eval/runner.py
  rasenloop_eval/assert_lib.py
packages/rasen-client/
  rasen_client/client.py
  rasen_client/transport.py
  rasen_client/fake.py
  rasen_client/models.py
  tests/...
packages/shared/
  shared/signals.py
  shared/schemas.py
scripts/bootstrap_rasen_agent.py
scripts/seed_db.py
Makefile
```

---

### Phase 0: Bootstrap monorepo + rasen-client

**Files:**
- Create: `README.md`, `.gitignore`, `Makefile`, `pyproject.toml`, `packages/rasen-client/**`, `apps/backend` skeleton, `apps/mcp-server` skeleton, `.env.example`
- Test: `packages/rasen-client/tests/test_idempotency_headers.py`

- [ ] **Step 0.1:** Add `.gitignore` (`.env`, `__pycache__`, `.venv`, `node_modules`, `*.db`, `.firecrawl`)
- [ ] **Step 0.2:** Add root `pyproject.toml` / workspace layout for backend, mcp-server, rasen-client, eval-harness
- [ ] **Step 0.3:** Implement `Transport` protocol + `FakeChaosTransport` returning canned `/context` and agent fixtures
- [ ] **Step 0.4:** Implement `RasenClient.create_agent` / `get_draft` / `patch_draft` that always send `Idempotency-Key` + `If-Match` where required
- [ ] **Step 0.5:** Tests: fake transport records headers; replay path sets persisted key
- [ ] **Step 0.6:** `Makefile` targets: `bootstrap`, `test`, `lint`
- [ ] **Step 0.7:** Commit + push: `chore: bootstrap monorepo and rasen-client fake transport`

**Exit criteria:** `make test` passes; fake client can “create” agent in memory.

---

### Phase 1: Domain + policy + MCP server

**Files:**
- Create: `apps/backend/app/models.py`, `policy.py`, `services/ledger.py`, `services/effects.py`, `apps/mcp-server/**`
- Test: `apps/backend/tests/test_policy.py`, `test_refund_idempotency.py`, `apps/mcp-server/tests/test_tools.py`

- [ ] **Step 1.1:** Define SQLAlchemy models for customers, transactions, effects, refunds, auth_sessions
- [ ] **Step 1.2:** Seed script with 4 demo customers (VIP eligible, cap exceed, fraud, OTP path)
- [ ] **Step 1.3:** Implement pure `check_refund_eligibility(customer, txn, auth) -> Decision`
- [ ] **Step 1.4:** Implement `execute_refund(effect_id, ...)` with UNIQUE(`effect_id`) and chaos hooks
- [ ] **Step 1.5:** Expose MCP Streamable HTTP tools: five tools listed in architecture
- [ ] **Step 1.6:** Tests: deny fraud; deny over cap; allow VIP; double effect_id no double money; chaos 503 leaves indeterminate-compatible state
- [ ] **Step 1.7:** Commit + push: `feat(mcp): policy-guarded ledger tools with effect_id idempotency`

**Exit criteria:** MCP tools callable locally with JSON-RPC/HTTP; policy tests green.

---

### Phase 2: Pre-call, agent bootstrap, webhooks

**Files:**
- Create: `apps/backend/app/api/pre_call.py`, `webhooks.py`, `scripts/bootstrap_rasen_agent.py`, webhook signature util
- Test: `test_webhook_signature.py`, `test_pre_call.py`

- [ ] **Step 2.1:** Implement Standard Webhooks verify (HMAC-SHA256, skew window, multi-sig)
- [ ] **Step 2.2:** `POST /pre-call/lookup_caller` returns ≤4KiB CRM JSON; timeout simulation
- [ ] **Step 2.3:** `POST /webhooks/rasen` verify → dedupe `webhook_id` → enqueue
- [ ] **Step 2.4:** Bootstrap script (live): create secret, register MCP, discover, create agent, pre_call tool, attach MCP tools, knowledge upload, transfer destinations, validate, publish, enable share-link
- [ ] **Step 2.5:** Fake-mode bootstrap writes local fixture agent config for offline demo
- [ ] **Step 2.6:** Document tunnel URLs in `.env.example`
- [ ] **Step 2.7:** Commit + push: `feat: pre_call CRM, webhooks, and Rasen agent bootstrap`

**Exit criteria:** Live or fake bootstrap produces a published agent config; webhook unit tests green; share-link steps documented.

---

### Phase 3: Reconciler + War Room + kill switch

**Files:**
- Create: `services/reconciler.py`, `api/war_room.py`, `apps/war-room/**`
- Test: `test_reconciler.py`, war-room smoke build

- [ ] **Step 3.1:** Reconciler scans `effects.status=indeterminate` or analyzed-call queue; resolves executed/failed
- [ ] **Step 3.2:** War Room API: list active calls, transcript proxy SSE, handoff brief, kill switch endpoint
- [ ] **Step 3.3:** Kill switch calls `RasenClient.revoke_secret_version`
- [ ] **Step 3.4:** Next.js UI: calls list, transcript pane, latency badges, kill button, brief card
- [ ] **Step 3.5:** Frustration score v0 (keyword/repetition heuristics on live text)
- [ ] **Step 3.6:** Commit + push: `feat(war-room): live transcript, reconciler, and secret kill switch`

**Exit criteria:** UI runs on `:3000`; reconciler test proves no double refund; kill switch unit-tested against fake.

---

### Phase 4: Signals + eval harness + auto-rollback

**Files:**
- Create: `services/signals.py`, `services/control_plane.py`, `apps/eval-harness/**`, `packages/shared/signals.py`
- Test: `test_signals.py`, `test_control_plane_rollback.py`, eval offline scenarios

- [ ] **Step 4.1:** Implement signal classifiers (grounding, latency, STT arg corruption, escalation loop)
- [ ] **Step 4.2:** On `call.analyzed` processing, persist signals + mirror tool runs
- [ ] **Step 4.3:** Eval harness scenarios (min 8) from [evals-and-chaos.md](./evals-and-chaos.md)
- [ ] **Step 4.4:** Runner uses `POST /agent-sessions` in live mode; fake completion in CI
- [ ] **Step 4.5:** Control plane: after publish, run evals; on blocker fail → rollback with `expected_live_version_id`
- [ ] **Step 4.6:** War Room panel shows last eval run + rollback receipt
- [ ] **Step 4.7:** Commit + push: `feat(control-plane): living evals and auto-rollback gate`

**Exit criteria:** Deliberately bad prompt fails eval and triggers rollback (fake fully; live if key present).

---

### Phase 5: Polish, CI, demo, field report

**Files:**
- Create: `.github/workflows/ci.yml`, finalize `demo-playbook.md`, `docs/field-report-template.md`
- Modify: README quickstart

- [ ] **Step 5.1:** CI workflow fake tests + war-room build
- [ ] **Step 5.2:** Rehearse demo-playbook cold; record Loom backup
- [ ] **Step 5.3:** Fill field-report template with real call_ids/metrics if live runs exist
- [ ] **Step 5.4:** README: architecture blurb + quickstart + link to docs
- [ ] **Step 5.5:** Final progress entry “Interview ready”
- [ ] **Step 5.6:** Commit + push: `docs+chore: CI, demo playbook, interview readiness`

**Exit criteria:** Checklist in [demo-playbook.md](./demo-playbook.md) all checked; repo public and green CI.

---

## Dependency graph

```text
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
              ↘_______________↗
           (policy shared by MCP + backend)
```

Do not start Phase 4 until reconciler + webhook intake exist (signals need analyzed call pipeline).

---

## Risk buffer

If behind schedule after Day 3:

1. Keep MCP + policy + reconciler + webhook signals (core thesis)
2. Simplify War Room to single-call transcript view
3. Run eval harness in fake mode for rollback demo; show one live share-link call separately
4. Drop transfer carrier wiring; keep destination config + spoken handoff

Never drop: effect_id idempotency, indeterminate reconcile, publish/rollback gate story.

---

## Progress tracking

Mark checkboxes in this file as you go **or** mirror completion in [engineering-progress.md](./engineering-progress.md) (preferred narrative log). Both should agree on which phase is current.

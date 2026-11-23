# What Is This Project?

**Project name:** RasenLoop Enterprise  
**Tagline:** Self-healing pan-India fintech voice customer support, with a closed-loop continual evaluation and auto-rollback control plane on top of the Rasen Developer API.  
**Repo:** [github.com/shiv-eshwar/rasenloop-enterprise](https://github.com/shiv-eshwar/rasenloop-enterprise)  
**Target interview:** Rasen Labs (Accel-backed voice AI research lab; founder Sparsh Agrawal)  
**Primary domain:** Pan-India digital bank / fintech customer support (UPI & card disputes, instant refunds, DTMF OTP, Fraud Desk)  
**Platform contract:** Rasen Developer API `https://api.rasen.ai/v1` (v1.14.0 as of 2026-11-14)

---

## One-paragraph pitch

RasenLoop Enterprise is not “a voice bot with a prompt.” It is an end-to-end **MNC fintech support system** that answers inbound Hinglish/English calls on Rasen, hydrates customer context before pickup, executes money-moving actions only through a **deterministic policy-guarded MCP server**, reconciles **indeterminate** tool outcomes safely, streams a live Supervisor War Room, and — most importantly — turns every production call into **living evals**. When a candidate agent publish regresses those evals under adversarial shadow traffic over `POST /agent-sessions`, the control plane **auto-rolls back** to the last good immutable version. That is Rasen’s exact thesis: **Build → Evaluate → Improve**, implemented as software an enterprise bank would trust.

---

## Why this exists

Rasen’s product and research story is continual learning for production voice agents: STT → LLM → TTS, Hindi/English/Hinglish, living evals from production signals, and approved model updates. Most intern demos only exercise “create agent + one webhook.” This project is designed so that if you were CEO of Rasen, you would hire the person who built it because it proves:

1. Deep fluency with the **real** Rasen API surface (draft/publish/rollback, `pre_call`, MCP discover, secrets revoke, tool-run forensics, live transcript SSE, signed webhooks, agent-sessions media, transfers, DTMF, usage).
2. Enterprise reliability around **money** (idempotent refunds, no double-pay, no hallucinated approvals).
3. Production ops thinking (war room, kill switch, reconciliation, regression gates).
4. Alignment with Rasen’s metrics: grounding, latency/tail latency, Indian STT→tool argument fidelity, TTS/tone under escalation.

---

## Problem statement

Large Indian fintech/bank contact centers fail in four ways that naive voice agents make worse:

| Failure mode | What happens today | What RasenLoop does |
| --- | --- | --- |
| Blind agent | Agent starts the call with no CRM context | `timing: "pre_call"` hydrates Customer 360 while the phone rings |
| Hallucinated refunds | LLM “approves” money the policy never allowed | MCP policy engine + structured deny/approve; LLM never owns the ledger |
| Partial failures | Payment gateway times out; agent retries and double-refunds | `effect_id` + outbox reconciler on `indeterminate` outcomes |
| Silent regressions | Prompt tweak ships; Hinglish grounding collapses | Living evals + shadow `agent-sessions` + automatic `rollback` |

---

## Product goals

### Primary goals (must ship for interview demo)

1. **Inbound fintech support agent** on Rasen (Hinglish + English) that can:
   - Greet the caller by name from pre-call CRM data
   - Authenticate with voice + DTMF OTP
   - Look up ledger/transactions
   - Check refund eligibility via deterministic policy
   - Execute refunds idempotently (or refuse with a clear spoken reason)
   - Create escalation tickets and schedule callbacks
   - Warm-transfer to Fraud Desk / Billing Disputes / VIP Retention / Tech L2
2. **MCP + webhook backend** that Rasen discovers and calls in production.
3. **Supervisor War Room** UI with live transcript SSE, frustration score, tool latency, handoff briefs, and mid-call secret kill switch.
4. **Continual-learning control plane** that classifies Production Signals from `call.analyzed` and can gate/rollback publishes.
5. **Eval harness** that drives synthetic adversarial callers over Rasen BYO-media WebSockets (`POST /agent-sessions`).

### Secondary goals (stretch if time allows)

- Campaign-based proactive dispute outreach (out of MVP core)
- Full SIP trunk / carrier import (demo can use hosted test-call links + agent-sessions)
- Multi-tenant workspace simulator

### Explicit non-goals (YAGNI for interview week)

- Replacing Rasen’s STT/LLM/TTS models (we *consume* Rasen; we do not reimplement the voice stack)
- Real bank core / NPCI / card-network integration (we use a realistic mock ledger with chaos toggles)
- Training APIs (not in the public Rasen API; we build the *outer* eval/rollback loop instead)
- Purchasing phone numbers via Rasen (import/assign if available; otherwise demo via share-link + agent-sessions)

---

## Success criteria (how we know it “worked”)

### Demo success (interview day)

- [ ] Interviewer can open a **Hosted Test-Call Link** and speak Hinglish to the agent.
- [ ] War Room shows the live transcript within ~1s of speech finalization.
- [ ] A refund attempt that violates policy is **spoken as denied**, and the ledger never moves.
- [ ] A chaos timeout on `execute_refund` produces `indeterminate`; reconciler resolves true state without double refund.
- [ ] Kill switch revokes the refund secret mid-call; subsequent mutating tool calls fail closed; call continues / transfers.
- [ ] Publishing a deliberately broken prompt fails living evals; control plane rolls back to previous `live_version_id`.
- [ ] A short Loom backup exists for network failure.

### Engineering success

- [ ] All mutating operations use persisted `Idempotency-Key` + correct `If-Match` ETags.
- [ ] Webhooks verify HMAC-SHA256 Standard Webhooks signatures and dedupe on `webhook-id`.
- [ ] Fake/Chaos Transport lets unit tests run without paid Rasen calls; live path works with real `RASEN_API_KEY`.
- [ ] Docs stay the source of truth: `whatthis.md`, `architecture.md`, `engineering.md`, `plan.md`, `engineering-progress.md`.

### Metric targets (demo-scale, not production SLA)

| Metric | Target |
| --- | --- |
| Pre-call CRM hydration | p95 &lt; 800ms (fail open if slower) |
| Tool latency alert threshold | `latency_ms` &gt; 2000 |
| Shadow eval suite | ≥ 8 adversarial scenarios green before promote |
| Double-refund rate under chaos | 0 |
| Auto-rollback on grounding regression | Triggered within one eval run after bad publish |

---

## Personas

| Persona | Need |
| --- | --- |
| **Caller (customer)** | Fast, natural Hinglish support; never repeat account digits on noisy lines; fair dispute outcome |
| **L2 Supervisor** | Live visibility, warm handoff context, ability to kill a compromised tool path |
| **Support Ops Lead** | Signal dashboard: grounding failures, STT corruption, latency spikes, escalation loops |
| **Platform Engineer (you)** | Safe publish/rollback, reproducible evals, Rasen API correctness |
| **Rasen interviewer** | Evidence you understand production voice systems and their continual-learning thesis |

---

## Domain model (fintech vertical)

Canonical entities in the mock bank:

- **Customer** — phone E.164, name, VIP tier (`standard` / `priority` / `vip`), KYC status, fraud flags
- **Account / Ledger** — balances, holds, recent UPI/card transactions
- **Dispute / Refund** — eligibility decision, policy code, amount cap, status (`proposed` / `executed` / `denied` / `indeterminate` / `reconciled`)
- **Ticket** — escalation queue, severity, linked call_id
- **Callback** — scheduled window, contact preference
- **Auth session** — OTP challenge via DTMF, step-up state for mutating tools
- **Effect** — durable idempotency record keyed by `effect_id` for mutating tools

Policy examples (deterministic, not LLM-owned):

- Refund only if transaction status is `failed` or `disputed_eligible`
- Cap: ₹5,000 auto; above that → create ticket + transfer Billing Disputes
- VIP may get higher auto-cap (₹25,000) with fraud_flag == false
- Any `fraud_flag` → refuse refund tools; transfer Fraud Desk
- Mutating tools require `auth_level >= otp_verified`

---

## Rasen capabilities this project deliberately exercises

| Capability | Rasen surface | RasenLoop use |
| --- | --- | --- |
| Agent lifecycle | draft / validate / publish / versions / rollback | Release engineering + auto-rollback |
| Pre-call tool | `timing: "pre_call"`, `system__caller_id` | Customer 360 hydration |
| MCP federation | register / discover / attach tools | Policy-guarded enterprise tools |
| Secrets | pin versions, rotate, **revoke mid-call** | Kill switch |
| Tool forensics | `tool-outcomes`, `listAgentToolRuns` | Signals + reconciliation |
| Live transcript | `GET /calls/{id}/transcript/live` | War Room |
| Webhooks | `call.completed` / `failed` / `analyzed` | Control plane intake |
| BYO media | `POST /agent-sessions` | Shadow eval callers |
| Transfers | named destinations | Fraud / Billing / VIP / Tech L2 |
| DTMF + PII vars | settings + sensitivity | OTP / card last-4 without STT risk |
| Usage | `/usage`, `/usage/query` | Cost per resolved ticket |
| Share links | hosted test-call link | Instant interview demo |
| Knowledge | FAQ / policy PDFs frozen at publish | Grounded policy answers |

---

## High-level system shape

```text
Caller (phone / browser share-link / eval bot)
        │
        ▼
   ┌─────────┐     pre_call webhook      ┌──────────────────┐
   │  Rasen  │ ─────────────────────────▶│  Core Backend    │
   │  Voice  │◀──── MCP tool calls ──────│  (FastAPI)       │
   │  Agent  │                           │  + Policy Engine │
   └────┬────┘                           │  + Ledger/Outbox │
        │ live SSE + webhooks            └────────┬─────────┘
        ▼                                         │
   ┌──────────────┐                      ┌────────▼─────────┐
   │ War Room UI  │                      │ Control Plane    │
   │ (Next.js)    │◀── signals/evals ────│ Eval + Rollback  │
   └──────────────┘                      └──────────────────┘
```

See [architecture.md](./architecture.md) for the full deep dive.

---

## Tech stack (locked)

| Layer | Choice |
| --- | --- |
| Backend / MCP / webhooks / reconciler / control plane | Python 3.12+, FastAPI, asyncio, SQLAlchemy 2.x, Pydantic v2 |
| Database | SQLite for local demo; Postgres-ready via DSN |
| War Room | Next.js (App Router) + React + TypeScript |
| Rasen client | Internal Python package with Fake/Chaos Transport |
| Eval harness | Python asyncio WebSocket client for `agent-sessions` (pcm16) |
| Secrets | `.env` locally; never commit keys |
| Docs | Markdown in `/docs` as source of truth |

---

## Repo layout (target)

```text
rasenloop-enterprise/
├── README.md
├── docs/
│   ├── whatthis.md              ← you are here
│   ├── architecture.md
│   ├── engineering.md
│   ├── plan.md
│   ├── engineering-progress.md
│   ├── api-contracts.md
│   ├── evals-and-chaos.md
│   ├── security-and-runbook.md
│   ├── demo-playbook.md
│   └── decisions/
├── apps/
│   ├── backend/                 # FastAPI: CRM, webhooks, war-room APIs, reconciler, control plane
│   ├── mcp-server/              # Streamable HTTP MCP + policy tools
│   ├── war-room/                # Next.js Supervisor UI
│   └── eval-harness/            # Shadow callers over agent-sessions
├── packages/
│   ├── rasen-client/            # Typed Rasen API client + fake transport
│   └── shared/                  # Shared schemas / signal taxonomies
├── scripts/                     # seed, bootstrap agent, demo runners
└── .github/workflows/           # CI: lint, unit, contract tests
```

---

## Risks and constraints (honest)

| Risk | Mitigation |
| --- | --- |
| Workspace concurrency default ~3 calls | Shadow suite runs sequentially / small batches; respect `Retry-After` + same Idempotency-Key |
| `pre_call` does not run on browser test calls | Document clearly; use real inbound when available; show pre_call via unit/integration + phone path |
| No public training API | Outer-loop living evals are the feature, not model fine-tuning |
| Network / Rasen outage during interview | Fake transport + Loom + share-link rehearsal |
| Time (interview next week) | Phased plan; Phase 0–4 are demo-critical; Phase 5+ are stretch |

---

## Glossary

| Term | Meaning |
| --- | --- |
| **Living eval** | An evaluation case derived from real or synthetic production-like calls, kept as a regression gate |
| **Production Signal** | Classified failure pattern (grounding, latency, STT corruption, escalation loop) |
| **Effect ID** | Client-supplied idempotency token for a mutating tool invocation |
| **Indeterminate** | Rasen tool outcome where side effect may or may not have applied — must reconcile, never blind-retry |
| **Publication token** | Draft ETag covering prompt, tools, MCP pins, secrets, knowledge — required for publish |
| **Kill switch** | `POST /secrets/{id}/versions/{v}/revoke` failing closed mid-call for compromised tools |

---

## Related docs

- [architecture.md](./architecture.md) — deep system design and data flows
- [engineering.md](./engineering.md) — how we build, test, ship
- [plan.md](./plan.md) — phased engineering plan
- [engineering-progress.md](./engineering-progress.md) — what was built each iteration
- [api-contracts.md](./api-contracts.md) — HTTP/MCP/webhook contracts
- [evals-and-chaos.md](./evals-and-chaos.md) — signal taxonomy and shadow suite
- [security-and-runbook.md](./security-and-runbook.md) — secrets, kill switch, ops
- [demo-playbook.md](./demo-playbook.md) — interview demo script

---

*Status: Spec locked for fintech vertical + Python/FastAPI + Next.js + live Rasen + Fake/Chaos Transport. Implementation follows [plan.md](./plan.md).*

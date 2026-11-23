# Engineering Workflow — RasenLoop Enterprise

How we design, build, test, document, and demo this project. Treat this as the team handbook for a one-person (or agent-assisted) engineering effort under interview deadline pressure.

Related: [whatthis.md](./whatthis.md) · [architecture.md](./architecture.md) · [plan.md](./plan.md) · [engineering-progress.md](./engineering-progress.md)

---

## 1. Engineering philosophy

1. **Docs first, then tests, then code.** Specs in `/docs` are the contract. If code disagrees with docs, update one deliberately — never leave them drifting.
2. **TDD for money and idempotency.** Ledger, effects, reconciler, webhook verify/dedupe, and rasen-client retry logic get tests *before* implementation.
3. **Vertical slices over horizontal layers.** Each phase ships a demoable slice (e.g., pre_call → MCP refund → war room line), not “all models then all APIs.”
4. **Fake transport by default in unit tests.** Live Rasen is for integration/demo scripts only.
5. **Small commits, pushed to GitHub.** Every meaningful slice gets a commit on `main` (or short-lived `feat/*` then merge). Push after each phase.
6. **YAGNI ruthlessly.** No microservices split, no Kubernetes, no real NPCI — mock bank + chaos is enough to prove the architecture.
7. **Interview artifact quality.** Readable README, reproducible `make demo`, Loom backup, call_ids in the field report.

---

## 2. Branching & commits

### Branching (interview week)

- Default: work on `main` with frequent pushes (solo speed).
- Use `feat/<phase>-<slug>` only if experimenting on a risky spike; merge fast.

### Commit message convention

```text
feat(mcp): add execute_refund with effect_id uniqueness
fix(reconciler): cover indeterminate then posted ledger
fix(war-room): stream live transcript with Last-Event-ID resume
docs(progress): mark Phase 2 complete
chore(ci): add ruff + pytest workflow
```

Types: `feat`, `fix`, `fix`, `docs`, `chore`, `refactor`, `demo`.

### Push policy

After each completed phase in [plan.md](./plan.md):

```bash
git add -A
git status
git commit -m "..."
git push -u origin HEAD
```

Update [engineering-progress.md](./engineering-progress.md) in the same commit when a phase completes.

---

## 3. Repository standards

### Python

- Python 3.12+
- Formatter/linter: `ruff`
- Type check: `mypy` (gradual; strict on `packages/rasen-client` and `policy`)
- Tests: `pytest` + `pytest-asyncio`
- HTTP: `httpx`
- API: FastAPI + Pydantic v2
- DB: SQLAlchemy 2.0 async or sync (pick sync SQLite for speed unless concurrency demands async)

### TypeScript (War Room)

- Next.js App Router
- TypeScript strict
- ESLint + Prettier
- Fetch to backend only (no Rasen keys in browser)

### Env management

```bash
# apps/backend/.env.example (committed)
RASEN_API_BASE=https://api.rasen.ai/v1
RASEN_API_KEY=
RASEN_TRANSPORT=fake   # fake | live
DATABASE_URL=sqlite:///./rasenloop.db
PUBLIC_BASE_URL=https://your-tunnel.example
WEBHOOK_SIGNING_SECRET=
MCP_AUTH_TOKEN=
WAR_ROOM_PASSWORD=dev
CONTROL_PLANE_AUTO_EVAL=1
CHAOS_MODE=0
```

Never commit `.env`. Rotate any key that accidentally leaks.

---

## 4. Daily engineering loop

```text
1. Read plan.md current phase + engineering-progress.md last entry
2. Write/adjust failing tests for the slice
3. Implement minimal code
4. Run unit tests (fake transport)
5. Optional: live smoke against Rasen (scripted)
6. Update engineering-progress.md checklist
7. Commit + push
8. If phase complete: update demo-playbook.md steps if UX changed
```

### Definition of Done for a task

- [ ] Tests pass locally
- [ ] No secrets in logs or repo
- [ ] API contract match [api-contracts.md](./api-contracts.md) if HTTP surface changed
- [ ] Progress doc updated
- [ ] Commit pushed to `shiv-eshwar/rasenloop-enterprise`

---

## 5. Testing strategy

### Layers

| Layer | What | Transport |
| --- | --- | --- |
| Unit | Policy engine, effect state machine, signature verify, signal classifiers | N/A / fake |
| Contract | rasen-client request shapes, Idempotency-Key persistence, ETag refresh logic | FakeChaosTransport |
| Integration | Backend + MCP + DB | Fake or live |
| Shadow eval | Full scenarios | Live preferred; fake for CI |
| Manual demo | Share-link + War Room | Live |

### Mandatory test themes

1. **Idempotent refund:** two `execute_refund` with same `effect_id` → one ledger row.
2. **Indeterminate reconcile:** timeout then row exists → `executed`; timeout then no row → `failed` (new effect_id allowed).
3. **Webhook dedupe:** same `webhook-id` twice → one process.
4. **Signature reject:** bad HMAC → 4xx, no enqueue.
5. **Kill switch:** revoke → next mutating tool surfaces `credential_unavailable` (fake) / live if available.
6. **Rollback gate:** failing eval triggers rollback client call with `expected_live_version_id`.
7. **Transcript SSE resume:** final:true not overwritten by final:false.

### Commands (target)

```bash
make test          # pytest packages + apps
make test-eval     # eval harness offline
make lint          # ruff + tsc
make smoke-live    # requires RASEN_TRANSPORT=live
```

---

## 6. Rasen integration rules (non-negotiable)

Copy these into code review mental checklist:

1. Persist `Idempotency-Key` **before** the HTTP call.
2. Never reuse a key with a different body.
3. On `idempotency_in_progress`, wait `Retry-After`, same key.
4. On `draft_conflict`, re-read draft, re-apply intent, new key + new If-Match.
5. On `at_capacity` / `quota_exceeded` for call start, wait `Retry-After`, **same** key.
6. Branch on `error.code`, not `error.message`.
7. Preserve unknown enum values.
8. Do not log `websocket_url`, raw secrets, or full PII.
9. Treat `indeterminate` tool outcomes as reconcile-only.
10. Pin secret versions in tools; rotation does not auto-move pins — replace tool pin + publish.

Connect Cursor to docs MCP while coding:

```json
{
  "mcpServers": {
    "rasen-docs": {
      "url": "https://docs.rasen.ai/_mcp/server"
    }
  }
}
```

---

## 7. Local runbook (dev)

### Prerequisites

- Python 3.12+, Node 22+, `uv` or `pip`, Docker optional
- Rasen workspace API key for live mode
- Tunnel tool for public webhooks/MCP

### Bootstrap

```bash
cp apps/backend/.env.example apps/backend/.env
# fill RASEN_API_KEY for live
make bootstrap   # install deps, create db, seed customers
make run-backend
make run-mcp
make run-war-room
make bootstrap-rasen-agent   # create/publish agent when live
```

### Seeding demo customers

Include at least:

| Phone (E.164) | Profile | Story |
| --- | --- | --- |
| `+9198…0001` | Priya Sharma, VIP | Failed UPI ₹1,299 eligible |
| `+9198…0002` | Rahul Verma, standard | Refund above cap → escalate |
| `+9198…0003` | Fraud-flagged account | Must transfer Fraud Desk |
| `+9198…0004` | OTP-required mutator | Happy path after DTMF |

---

## 8. CI/CD

GitHub Actions on push to `main`:

1. Checkout
2. Setup Python/Node
3. `ruff check` + `pytest` (fake transport)
4. `npm ci && npm run lint && npm run build` for war-room
5. Upload eval offline report artifact

No automatic live Rasen calls in CI (cost + flakey network). Optional manual `workflow_dispatch` smoke.

---

## 9. Documentation hygiene

| Doc | Update when |
| --- | --- |
| `whatthis.md` | Goals/scope change |
| `architecture.md` | New component or flow |
| `engineering.md` | Process/tooling change |
| `plan.md` | Phase order/scope change (checkboxes) |
| `engineering-progress.md` | **Every iteration / phase completion** |
| `api-contracts.md` | Any HTTP/MCP field change |
| `evals-and-chaos.md` | New scenario or signal type |
| `security-and-runbook.md` | Secret/kill-switch/ops change |
| `demo-playbook.md` | Demo script change |
| `decisions/*.md` | Non-obvious tradeoff locked |

### Progress entry template

```markdown
### YYYY-MM-DD — Phase N / Iteration K
- Goal:
- Built:
- Tests:
- Live Rasen notes (call_ids / request_ids):
- Blockers:
- Next:
```

---

## 10. Agent-assisted development protocol

When using Cursor agents on this repo:

1. Point them at `docs/plan.md` current phase only — avoid boiling the ocean.
2. Require FakeChaosTransport tests with the feature.
3. Forbid committing `.env` or real secrets.
4. After code, require progress doc update.
5. Prefer `packages/rasen-client` changes to be contract-tested.

---

## 11. Quality bar for “interview ready”

- [ ] Cold start: clone → `make bootstrap` → fake demo path works
- [ ] Live path documented; share-link opens
- [ ] War Room shows a live or recorded call
- [ ] One chaos indeterminate refund reconciled correctly
- [ ] One bad publish auto-rolled back (live or fake control-plane test)
- [ ] Field report draft with metrics + 3 DX observations
- [ ] Loom ≤ 3 minutes as backup

---

## 12. Make targets (intended)

```makefile
bootstrap          Install + db migrate + seed
run-backend        uvicorn backend
run-mcp            uvicorn mcp-server
run-war-room       next dev
bootstrap-rasen-agent  Create tools/MCP/publish via client
test               Unit + contract
test-eval          Offline eval suite
smoke-live         minimal live call/session
demo               scripted demo checklist printer
lint               ruff + tsc
```

---

*Engineering is successful when a stranger can run the fake path, and you can run the live interview demo without tribal knowledge outside `/docs`.*

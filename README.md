# RasenLoop Enterprise

**Self-healing pan-India fintech voice customer support** on the [Rasen Developer API](https://docs.rasen.ai/welcome) — with CRM pre-call hydration, policy-guarded MCP tools, indeterminate refund reconciliation, a live Supervisor War Room, living evals, and **auto-rollback** on regressions.

> Built as a high-complexity interview/portfolio system aligned with Rasen’s thesis: **Build → Evaluate → Improve**.

**GitHub:** [github.com/shiv-eshwar/rasenloop-enterprise](https://github.com/shiv-eshwar/rasenloop-enterprise)

---

## Why this exists

Naive voice agents hallucinate refunds, double-charge on timeouts, and ship prompt regressions silently. RasenLoop treats support like a distributed money system:

1. **`pre_call`** hydrates Customer 360 while the phone rings  
2. **MCP policy engine** decides eligibility — the LLM never owns the ledger  
3. **`effect_id` + reconciler** make refunds safe under `indeterminate` outcomes  
4. **War Room** streams live transcripts + mid-call **secret kill switch**  
5. **Shadow evals** over `POST /agent-sessions` gate publishes and **auto-rollback**

---

## Documentation (start here)

| Doc | Purpose |
| --- | --- |
| [docs/whatthis.md](docs/whatthis.md) | What the project is, goals, non-goals, success criteria |
| [docs/architecture.md](docs/architecture.md) | Deep end-to-end architecture & flows |
| [docs/engineering.md](docs/engineering.md) | Engineering workflow, testing, Rasen integration rules |
| [docs/plan.md](docs/plan.md) | Phased implementation plan (checkboxes) |
| [docs/engineering-progress.md](docs/engineering-progress.md) | Living progress log (update every iteration) |
| [docs/api-contracts.md](docs/api-contracts.md) | HTTP/MCP/webhook contracts |
| [docs/evals-and-chaos.md](docs/evals-and-chaos.md) | Signal taxonomy, scenarios, chaos |
| [docs/security-and-runbook.md](docs/security-and-runbook.md) | Secrets, kill switch, incidents |
| [docs/demo-playbook.md](docs/demo-playbook.md) | Interview demo script |
| [docs/field-report-template.md](docs/field-report-template.md) | DX / metrics report for interviewers |
| [docs/decisions/](docs/decisions/) | Architecture Decision Records |

---

## Target stack

- **Backend / MCP / Control plane / Eval harness:** Python 3.12, FastAPI, SQLAlchemy, Pydantic v2  
- **War Room:** Next.js (App Router), React, TypeScript  
- **Voice platform:** Rasen API `https://api.rasen.ai/v1` (v1.14.0+)  
- **DB:** SQLite locally (Postgres-ready)  
- **Tests:** Fake/Chaos Rasen transport by default; live optional  

---

## Status

**Phase:** Documentation bootstrap complete → implementation starts at **Phase 0** in [docs/plan.md](docs/plan.md).

```text
apps/       # backend, mcp-server, war-room, eval-harness (to be filled)
packages/   # rasen-client, shared (to be filled)
docs/       # source of truth (current)
scripts/    # bootstrap / seed (to be filled)
```

---

## Quickstart (after Phase 0 lands)

```bash
git clone https://github.com/shiv-eshwar/rasenloop-enterprise.git
cd rasenloop-enterprise
cp apps/backend/.env.example apps/backend/.env   # add RASEN_API_KEY for live
make bootstrap
make test          # fake transport
make run-backend   # :8000
make run-mcp       # :8001
make run-war-room  # :3000
```

Live agent bootstrap and share-link steps: see `docs/engineering.md` and `docs/demo-playbook.md`.

---

## Cursor + Rasen docs MCP

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

## License

MIT (unless otherwise noted). Demo bank data is fictional.

# Demo Playbook — RasenLoop Enterprise (Interview)

**Audience:** Rasen Labs interviewers  
**Length:** 8–12 minutes live + 2-minute Loom backup  
**Goal:** Prove Build → Evaluate → Improve on a money-moving fintech voice agent

---

## 0. Pre-flight (30 minutes before)

- [ ] `git status` clean on latest `main`
- [ ] `make bootstrap` / services up: backend `:8000`, MCP `:8001`, war-room `:3000`
- [ ] Tunnel healthy; Rasen webhook + MCP URLs reachable
- [ ] `RASEN_TRANSPORT=live` and key valid (`GET /context`)
- [ ] Share-link enabled; token saved offline
- [ ] War Room login works
- [ ] Seed customers loaded (Priya VIP, Rahul cap, Fraud flag)
- [ ] Loom backup file open locally
- [ ] Kill-switch secret version known (current pin)
- [ ] One “bad prompt” patch prepared for rollback demo (stash or script)

---

## 1. Narrative arc (say this)

> “Most voice demos are a prompt and a webhook. RasenLoop is a fintech support system that hydrates CRM before pickup, refuses hallucinated refunds via a policy MCP server, reconciles indeterminate payment outcomes, gives supervisors a live war room with a mid-call credential kill switch, and auto-rolls back bad publishes when living evals fail — which is Rasen’s Build → Evaluate → Improve loop as software.”

---

## 2. Live script

### Act A — Happy path (3 min)

1. Open War Room active calls view.
2. Interviewer calls share-link (or you call).
3. Speak Hinglish: failed UPI refund for Priya.
4. Show live transcript streaming.
5. Complete DTMF OTP if prompted.
6. Show tool latency badges / ledger tool results in brief.
7. Confirm refund executed once; agent summarizes.

**Point to:** policy allow + single `effect_id`.

### Act B — Policy denial (1.5 min)

1. Switch to Rahul / large amount story (or second share session).
2. Show denial + escalation/ticket or transfer intent — **no money movement**.

**Point to:** LLM does not own the ledger.

### Act C — Chaos indeterminate (2 min)

1. Enable chaos timeout on `execute_refund`.
2. Run path that hits refund.
3. Show agent not confidently claiming success.
4. Show reconciler resolving effect without double refund.

**Point to:** `indeterminate` handling per Rasen docs.

### Act D — Kill switch (1.5 min)

1. Click War Room Kill Switch.
2. Attempt another mutating tool / show `credential_unavailable` path.
3. Show call can still transfer / continue talking.

**Point to:** Rasen pinned secret revoke fails closed mid-call.

### Act E — Auto-rollback (3 min)

1. Publish deliberately bad prompt (scripted).
2. Control plane runs shadow eval (show panel).
3. Blocker fails → rollback receipt.
4. Confirm `live_version_id` restored.

**Point to:** immutable versions + `expected_live_version_id` rollback.

---

## 3. If something breaks

| Breakage | Fallback |
| --- | --- |
| Share-link audio fails | Play Loom Act A–E |
| Live eval too slow | Show recorded eval report JSON + fake control-plane test |
| Tunnel down | Fake transport UI story + architecture diagram |
| Concurrent capacity | Explain Retry-After + serial evals; show logs |

Never debug silently for &gt;60 seconds — narrate and switch to backup.

---

## 4. Closing lines (30s)

> “The interesting part isn’t that the agent talks. It’s that production signals become living evals, and releases can’t silently regress grounding on Hinglish money conversations. Happy to go deeper on rasen-client idempotency, MCP policy, or the eval harness next.”

Hand them: repo URL, field report, 1–2 call_ids.

---

## 5. Post-demo checklist

- [ ] Disable chaos mode
- [ ] Re-publish known-good agent if needed
- [ ] Rotate demo secrets if interviewer used kill switch on shared workspace
- [ ] Log outcomes in `engineering-progress.md`

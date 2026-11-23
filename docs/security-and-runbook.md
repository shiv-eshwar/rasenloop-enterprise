# Security & Operations Runbook — RasenLoop Enterprise

---

## 1. Trust boundaries

| Zone | Allowed secrets | Notes |
| --- | --- | --- |
| Browser / War Room client | Session token only | No Rasen API key |
| Backend | `RASEN_API_KEY`, webhook secrets, DB | Server-side only |
| MCP server | MCP bearer, DB creds | Separate token from webhook tool secret |
| Eval harness | `RASEN_API_KEY` | Local/CI secret store |
| GitHub | None of the above | Use Actions secrets if needed later |

Rasen separates secret **purposes**: `webhook_tool` vs `mcp_server`. Do not cross-wire.

---

## 2. Secret lifecycle

### Create

```text
POST /secrets { purpose, name, resource_key, value }
→ pin {secret_id, version} on tool header or MCP server
→ publish agent
```

### Rotate (safe)

1. `POST /secrets/{id}/versions` with new value (pins unchanged)
2. `GET /secrets/{id}/references?version=old`
3. Replace each consumer pin to new version
4. Validate + publish each agent
5. When no `live: true` references remain, revoke old version

### Emergency kill switch (War Room)

```text
POST /war-room/kill-switch { reason: "compromised" }
→ POST /secrets/{id}/versions/{v}/revoke { reason: "compromised" }
```

Effects:

- In-flight and future tool calls using that pin fail with `credential_unavailable`
- Call audio continues; transfer still possible if not secret-dependent
- Revocation **cannot be undone** — rotate new version + republish to recover

---

## 3. PII & logging rules

**Never log:**

- Raw OTP codes
- Full PANs / full account numbers
- `Authorization` headers
- Webhook signing secrets
- `websocket_url` from agent-sessions
- Unredacted transcripts in public issues

**Do log:**

- `call_id`, `agent_id`, `published_version_id`
- `X-Request-Id` / `request_id`
- Tool names, `latency_ms`, `state`, `reason`
- Effect ids (not bank passwords)

Rasen variable sensitivity: mark `otp_code` as `confidential`, `card_last4` as `pii`.

---

## 4. Webhook hardening

1. HTTPS only, public DNS (Rasen refuses private destinations)
2. Verify signature before processing
3. Timestamp skew ≤ 5 minutes
4. Dedupe `webhook-id`
5. Rotate signing secret with 24h dual-verify grace
6. Monitor `disabled_failing` state if endpoint unhealthy

---

## 5. AuthN/Z for War Room

MVP: single shared password → HTTP-only session cookie.

Privileged actions:

- Kill switch
- Force eval / force rollback
- View raw tool argument payloads (may contain txn ids)

Production-future: SSO — out of scope for interview week.

---

## 6. Incident runbooks

### INC-1 — Suspected prompt injection draining refunds

1. Hit **Kill Switch** immediately
2. Pause share-link / inbound assignment if possible
3. Query ledger for refunds in last N minutes
4. Snapshot call_ids with `execute_refund` runs
5. Rollback agent to last known good version
6. Rotate MCP secret; republish with new pin
7. Write field notes with evidence

### INC-2 — Double refund reported

1. Look up `effect_id` / `txn_id` in `effects` + `refunds`
2. If two rows with different effect_ids: policy/process bug — stop agent
3. If indeterminate stuck: run reconciler manually
4. Add regression test before re-enable

### INC-3 — Eval gate flapping

1. Check workspace concurrency / `at_capacity`
2. Re-run suite serially
3. Inspect fake vs live drift
4. Do not disable gate silently — document waiver in progress log

### INC-4 — Webhook signature failures

1. Confirm secret rotation grace
2. Check clock skew on host
3. Resend delivery via Rasen API if needed
4. Ensure raw body used for HMAC (not re-serialized JSON)

---

## 7. Capacity & rate limits (Rasen)

| Class | Per key / min | Notes |
| --- | --- | --- |
| Reads | 60 | includes search/usage query |
| Call starts | 10 | createCall + createAgentSession |
| Authoring writes | 30 | |
| Ingestion/discovery | 5 | |

Default workspace concurrent calls often **3**. Eval harness must respect `Retry-After` and same Idempotency-Key.

---

## 8. Backup & demo resilience

- Loom backup of happy path + rollback
- Fake transport demo path when network dies
- Seed DB committed as fixture SQL/JSON (no secrets)
- Document tunnel restart steps in demo-playbook

---

## 9. Compliance posture (honest)

This project **demonstrates** controls aligned with bank-like expectations (OTP step-up, audit effects, redaction, kill switch). It is **not** a certified PCI/RBI deployment. Say this explicitly in interviews if asked.

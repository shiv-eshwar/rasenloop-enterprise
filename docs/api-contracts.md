# API Contracts — RasenLoop Enterprise

Contracts for **our** HTTP/MCP surfaces and the **Rasen** operations we depend on. Field names here are normative for implementers.

---

## 0. Conventions

- JSON, UTF-8, `Content-Type: application/json`
- Times: RFC 3339 UTC
- Money: integer **paise** internally optional; API examples use `amount_inr` as decimal string with 2 places for readability — pick one in code and stick to it (`amount_inr_paise: int` preferred)
- IDs: ULID or UUID strings
- Errors:

```json
{
  "error": {
    "code": "policy_denied",
    "message": "Refund exceeds auto-cap",
    "details": { "policy_code": "CAP_EXCEEDED" }
  }
}
```

Branch on `error.code`.

---

## 1. Pre-call webhook (Rasen → Backend)

**Endpoint:** `GET|POST /pre-call/lookup_caller`  
(Rasen webhook tool; prefer GET with query param from `system__caller_id`)

### Request

| Field | Source | Notes |
| --- | --- | --- |
| `phone` | query/path from `system__caller_id` | E.164 |
| `X-Api-Key` | secret header | pinned Rasen secret version |

### Response 200 (≤ 4096 bytes)

```json
{
  "name": "Priya Sharma",
  "customer_id": "cust_01",
  "vip_tier": "vip",
  "fraud_flag": false,
  "language_preference": "hinglish",
  "open_incidents": [
    { "id": "inc_9", "summary": "UPI failed debit under review" }
  ],
  "recent_failed_transactions": [
    {
      "txn_id": "txn_55",
      "amount_inr": "1299.00",
      "channel": "upi",
      "status": "failed",
      "merchant": "RailYatri"
    }
  ],
  "auth_hint": "otp_required_for_refunds"
}
```

### Fail-open

- On our 5xx/timeout, Rasen continues call without injection.
- We still log `pre_call_miss`.

---

## 2. MCP tools (Rasen → MCP server)

Auth: bearer token (`purpose: mcp_server` secret).

### 2.1 `get_customer_ledger`

**Input:**

```json
{ "customer_id": "cust_01", "limit": 5 }
```

**Output:**

```json
{
  "customer_id": "cust_01",
  "available_balance_inr": "15420.55",
  "transactions": [
    {
      "txn_id": "txn_55",
      "amount_inr": "1299.00",
      "channel": "upi",
      "status": "failed",
      "created_at": "2026-11-20T08:11:00Z",
      "merchant": "RailYatri"
    }
  ]
}
```

### 2.2 `check_refund_eligibility`

**Input:**

```json
{
  "customer_id": "cust_01",
  "txn_id": "txn_55",
  "call_id": "call_…",
  "requested_amount_inr": "1299.00"
}
```

**Output (allow):**

```json
{
  "decision": "allow",
  "policy_code": "ELIGIBLE_FAILED_UPI",
  "max_amount_inr": "1299.00",
  "requires_otp": true,
  "reasons": ["transaction_failed", "within_vip_cap"]
}
```

**Output (deny):**

```json
{
  "decision": "deny",
  "policy_code": "FRAUD_FLAG",
  "max_amount_inr": "0.00",
  "requires_otp": false,
  "reasons": ["fraud_flag_set"],
  "recommended_transfer": "Fraud Desk"
}
```

### 2.3 `execute_refund`

**Input:**

```json
{
  "customer_id": "cust_01",
  "txn_id": "txn_55",
  "amount_inr": "1299.00",
  "call_id": "call_…",
  "effect_id": "eff_01hxyz…",
  "auth_token": "otp_session_…"
}
```

Rasen tool config should send `effect_id` via **`effect_id_name` header** when supported by our webhook mirror; for MCP, include in arguments and enforce server-side.

**Output (executed):**

```json
{
  "status": "executed",
  "refund_id": "ref_01",
  "effect_id": "eff_01hxyz…",
  "amount_inr": "1299.00"
}
```

**Output (duplicate effect):**

```json
{
  "status": "executed",
  "refund_id": "ref_01",
  "effect_id": "eff_01hxyz…",
  "idempotent_replay": true
}
```

**Errors:** `auth_required`, `policy_denied`, `chaos_timeout` (may leave indeterminate upstream)

### 2.4 `create_escalation_ticket`

```json
{
  "customer_id": "cust_01",
  "queue": "Billing Disputes",
  "severity": "high",
  "summary": "Cap exceeded refund request",
  "call_id": "call_…",
  "effect_id": "eff_…"
}
```

→ `{ "ticket_id": "tkt_…", "status": "open" }`

### 2.5 `schedule_callback`

```json
{
  "customer_id": "cust_01",
  "window_start": "2026-11-24T14:00:00Z",
  "window_end": "2026-11-24T15:00:00Z",
  "call_id": "call_…",
  "effect_id": "eff_…"
}
```

→ `{ "callback_id": "cb_…", "status": "scheduled" }`

---

## 3. Rasen webhooks (Rasen → Backend)

**Endpoint:** `POST /webhooks/rasen`

### Headers

- `webhook-id`, `webhook-timestamp`, `webhook-signature`
- `user-agent: Rasen-Webhooks/1.0`

### Envelope

```json
{
  "id": "wevt_…",
  "type": "call.analyzed",
  "created_at": "2026-11-23T10:00:00.000Z",
  "workspace_id": "ws_…",
  "api_version": "1.14.0",
  "data": {}
}
```

### Handling rules

1. Verify signature before JSON parse consumers rely on
2. Reject skew &gt; 300s
3. Dedupe on `id` / `webhook-id`
4. Ack 2xx fast; process async
5. Unknown `type` → 2xx ignore
6. If `data.truncated === true` → `GET /calls/{call_id}`

---

## 4. War Room API (Browser → Backend)

Auth: session cookie or `Authorization: Bearer <war_room_token>` (demo password).

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/war-room/calls?active=1` | Active/recent calls |
| `GET` | `/war-room/calls/{call_id}` | Detail + brief |
| `GET` | `/war-room/calls/{call_id}/transcript/live` | SSE proxy to Rasen live transcript |
| `POST` | `/war-room/kill-switch` | Body: `{ "reason": "compromised" }` → revoke refund secret version |
| `GET` | `/war-room/signals?limit=50` | Recent production signals |
| `GET` | `/war-room/evals/latest` | Latest eval run + rollback info |
| `POST` | `/war-room/evals/run` | Manual trigger shadow suite |

### Kill switch request

```json
{ "reason": "compromised", "secret_resource_key": "mcp-refund-prod" }
```

### Kill switch response

```json
{
  "revoked_version": 3,
  "secret_id": "sec_…",
  "rasen_request_id": "req_…"
}
```

---

## 5. OTP API (Agent tools / internal)

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/otp/start` | `{ customer_id, call_id }` → `{ session_id, expires_at }` (OTP sent via mock channel / logged in demo) |
| `POST` | `/otp/verify` | `{ session_id, code }` → `{ verified: true, auth_token }` |

DTMF: agent collects digits into confidential variable; tool passes code to verify.

---

## 6. Rasen client operations we wrap (checklist)

| Operation | Path | Notes |
| --- | --- | --- |
| Context | `GET /context` | Key probe |
| Create agent | `POST /agents` | Idempotency-Key |
| Draft get/patch | `GET/PATCH /agents/{id}/draft` | If-Match |
| Validate | `POST /agents/{id}/draft/validate` | If-Match, no idem key |
| Publish | `POST /agents/{id}/publish` | If-Match + Idempotency-Key |
| Rollback | `POST /agents/{id}/rollback` | `expected_live_version_id` |
| Tools create | `POST /agents/{id}/tools` | `timing: pre_call` supported |
| MCP create/discover | `/mcp-servers` | streamable_http |
| Secrets | `/secrets` | revoke version for kill switch |
| Calls | `/calls` | results + tool-outcomes |
| Live transcript | `GET /calls/{id}/transcript/live` | SSE |
| Agent sessions | `POST /agent-sessions` | eval harness |
| Webhook endpoints | `/webhook-endpoints` | manage receivers |
| Share link | `/agents/{id}/share-link` | demo |
| Usage | `/usage`, `/usage/query` | cost metrics |

Exact schemas: prefer live docs via `https://docs.rasen.ai/_mcp/server` and `*.md` pages while implementing.

---

## 7. Control plane internal events

```json
{
  "type": "eval_completed",
  "eval_run_id": "er_…",
  "candidate_version_id": "pub_…",
  "passed": false,
  "blocker_scenarios": ["grounding_unverified_refund_promise"],
  "rollback": {
    "attempted": true,
    "to_version_id": "pub_prev",
    "receipt": {}
  }
}
```

---

## 8. Versioning

- Our public HTTP APIs are unversioned for interview (`/war-room/...`).
- Pin documented Rasen `api_version` observed in webhooks; tolerate newer.
- Shared signal type strings live in `packages/shared` and must match [evals-and-chaos.md](./evals-and-chaos.md).

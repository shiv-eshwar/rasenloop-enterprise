"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const PASSWORD = process.env.NEXT_PUBLIC_WAR_ROOM_PASSWORD || "dev";

type CallItem = {
  call_id: string;
  agent_id?: string;
  state?: string;
  active?: boolean;
};

async function api(path: string, init?: RequestInit) {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${PASSWORD}`,
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

export default function WarRoomPage() {
  const [calls, setCalls] = useState<CallItem[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [signals, setSignals] = useState<any[]>([]);
  const [evalLatest, setEvalLatest] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const [c, s, e] = await Promise.all([
        api("/war-room/calls?active=0"),
        api("/war-room/signals?limit=20"),
        api("/war-room/evals/latest"),
      ]);
      setCalls(c.items || []);
      setSignals(s.items || []);
      setEvalLatest(e.eval);
      if (!selected && c.items?.[0]?.call_id) {
        setSelected(c.items[0].call_id);
      }
    } catch (err: any) {
      setError(err.message || String(err));
    }
  }, [selected]);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 4000);
    return () => clearInterval(t);
  }, [refresh]);

  useEffect(() => {
    if (!selected) return;
    api(`/war-room/calls/${selected}`)
      .then(setDetail)
      .catch((err) => setError(err.message));
  }, [selected]);

  const frustration = detail?.frustration_score ?? 0;
  const frustrationClass = useMemo(() => {
    if (frustration >= 60) return "bad";
    if (frustration >= 30) return "warn";
    return "ok";
  }, [frustration]);

  async function seedDemoCall() {
    setBusy(true);
    try {
      const created = await api("/war-room/demo/active-call", { method: "POST" });
      setSelected(created.call_id);
      await refresh();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function killSwitch() {
    setBusy(true);
    try {
      await api("/war-room/kill-switch", {
        method: "POST",
        body: JSON.stringify({ reason: "compromised" }),
      });
      await refresh();
      alert("Kill switch engaged — refund secret version revoked.");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function runEval() {
    setBusy(true);
    try {
      const result = await api("/war-room/evals/run", {
        method: "POST",
        body: JSON.stringify({
          agent_id: "agent_demo",
          candidate_version_id: "pub_candidate_bad",
          previous_version_id: "pub_previous_good",
        }),
      });
      setEvalLatest({
        id: result.eval_run_id,
        status: result.passed ? "passed" : "failed_rolled_back",
        report: result.report,
        candidate_version_id: "pub_candidate_bad",
      });
      await refresh();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <header>
        <h1>RasenLoop War Room</h1>
        <p>BharatPay voice support — live ops, kill switch, living evals</p>
      </header>

      <div className="row" style={{ marginTop: "1rem" }}>
        <button className="primary" onClick={refresh} disabled={busy}>
          Refresh
        </button>
        <button onClick={seedDemoCall} disabled={busy}>
          Seed demo call
        </button>
        <button className="danger" onClick={killSwitch} disabled={busy}>
          Kill switch
        </button>
        <button onClick={runEval} disabled={busy}>
          Run shadow eval
        </button>
      </div>
      {error ? <p className="error">{error}</p> : null}

      <div className="grid">
        <section className="panel">
          <h2>Active / recent calls</h2>
          <div className="list">
            {calls.length === 0 ? (
              <div className="meta">No calls yet — seed a demo call.</div>
            ) : (
              calls.map((c) => (
                <button
                  key={c.call_id}
                  className={`item ${selected === c.call_id ? "active" : ""}`}
                  onClick={() => setSelected(c.call_id)}
                  style={{ textAlign: "left" }}
                >
                  <div>{c.call_id}</div>
                  <div className="meta">
                    {c.state || "unknown"} {c.active ? "· active" : ""}
                  </div>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="panel">
          <h2>Call detail</h2>
          {detail ? (
            <>
              <div className="row">
                <span className={`badge ${frustrationClass}`}>
                  Frustration {frustration}
                </span>
                <span className="badge">{detail.state}</span>
              </div>
              <div className="meta" style={{ marginBottom: "0.5rem" }}>
                Handoff brief: {detail.brief?.identity} · {detail.brief?.unresolved_blocker || "none"}
              </div>
              <div className="transcript">{detail.transcript_text || "No transcript yet"}</div>
            </>
          ) : (
            <div className="meta">Select a call</div>
          )}
        </section>

        <section className="panel">
          <h2>Production signals</h2>
          <div className="list">
            {signals.length === 0 ? (
              <div className="meta">No signals</div>
            ) : (
              signals.map((s) => (
                <div className="item" key={s.id}>
                  <div>
                    <span className={`badge ${s.severity === "blocker" || s.severity === "critical" ? "bad" : "warn"}`}>
                      {s.severity}
                    </span>{" "}
                    {s.signal_type}
                  </div>
                  <div className="meta">{s.call_id}</div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="panel">
          <h2>Latest eval / rollback</h2>
          {evalLatest ? (
            <>
              <div className="row">
                <span className={`badge ${String(evalLatest.status).includes("pass") ? "ok" : "bad"}`}>
                  {evalLatest.status}
                </span>
              </div>
              <div className="meta">candidate: {evalLatest.candidate_version_id}</div>
              <pre className="transcript" style={{ marginTop: "0.75rem" }}>
                {JSON.stringify(evalLatest.report || {}, null, 2)}
              </pre>
            </>
          ) : (
            <div className="meta">No eval runs yet</div>
          )}
        </section>
      </div>
    </main>
  );
}

"use client";

import { useState } from "react";
import Page from "@/components/Page";
import { api } from "@/lib/api";

export default function Login() {
  const [email, setEmail] = useState("demo@runbook.local");
  const [displayName, setDisplayName] = useState("Demo User");
  const [result, setResult] = useState<any>();
  const [error, setError] = useState("");

  async function login() {
    setError("");
    try {
      const payload = await api("/api/auth/dev-login", {
        method: "POST",
        body: JSON.stringify({ email, display_name: displayName }),
      });
      localStorage.setItem("runbook_token", payload.token);
      setResult(payload);
    } catch (exc: any) {
      setError(exc.message);
    }
  }

  return (
    <Page
      title="Runbook Login"
      description="Authenticate into a workspace before connecting source systems."
    >
      <div className="grid two">
        <section className="card card-pad stack">
          <h2>Dev login</h2>
          <p className="subtle">
            Local dev mode creates a real user, session, workspace, and owner membership.
          </p>
          <div className="field">
            <label>Email</label>
            <input value={email} onChange={(event) => setEmail(event.target.value)} />
          </div>
          <div className="field">
            <label>Display name</label>
            <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
          </div>
          <button className="button" onClick={login}>
            Continue
          </button>
          {error && <div className="notice error">{error}</div>}
          {result && (
            <div className="notice">
              Logged in as {result.user.display_name}. Active workspace:{" "}
              {result.user.workspaces?.[0]?.name || "Local workspace"}.
            </div>
          )}
        </section>
        <section className="card card-pad stack">
          <h2>Enterprise providers</h2>
          <div className="row between">
            <span>Google</span>
            <span className="badge">Configured by env</span>
          </div>
          <div className="row between">
            <span>GitHub</span>
            <span className="badge">Configured by env</span>
          </div>
          <div className="row between">
            <span>Microsoft / Entra ID</span>
            <span className="badge">Configured by env</span>
          </div>
          <p className="subtle">
            Provider OAuth can issue the same backend session model used by dev login.
          </p>
        </section>
      </div>
    </Page>
  );
}

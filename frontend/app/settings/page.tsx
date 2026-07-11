"use client";

import { useEffect, useState } from "react";
import Page from "@/components/Page";
import { api } from "@/lib/api";

export default function Settings() {
  const [settings, setSettings] = useState<any>();
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/settings/runtime").then(setSettings).catch((exc) => setError(exc.message));
  }, []);

  return (
    <Page title="Settings" description="Runtime safety, authentication, and infrastructure configuration.">
      {error && <div className="notice error">{error}</div>}
      <div className="grid two">
        <section className="card card-pad stack">
          <h2>Execution</h2>
          <SettingRow label="Demo mode" enabled={settings?.runbook_demo_mode} />
          <SettingRow label="Local command execution" enabled={settings?.allow_local_command_execution} />
          <p className="subtle">
            Dangerous commands are preview-only unless local execution is explicitly enabled.
          </p>
        </section>
        <section className="card card-pad stack">
          <h2>Memory and policy</h2>
          <div className="row between">
            <span>Graph backend</span>
            <strong>{settings?.graph_backend || "arcadedb"}</strong>
          </div>
          <div className="row between">
            <span>ArcadeDB database</span>
            <strong>{settings?.arcadedb_database || "runbook"}</strong>
          </div>
          <SettingRow label="HCAG routing" enabled={settings?.hcag_enabled} />
          <SettingRow label="AgentGate policy" enabled={settings?.agentgate_enabled} />
        </section>
        <section className="card card-pad stack">
          <h2>Application auth</h2>
          <SettingRow label="Dev login" enabled={settings?.auth_dev_mode} />
          <div className="row between">
            <span>Environment</span>
            <strong>{settings?.environment || "development"}</strong>
          </div>
        </section>
        <section className="card card-pad stack">
          <h2>Connector auth</h2>
          <SettingRow label="GitHub OAuth configured" enabled={settings?.github_oauth_configured} />
          <SettingRow label="Slack OAuth configured" enabled={settings?.slack_oauth_configured} />
        </section>
      </div>
    </Page>
  );
}

function SettingRow({ label, enabled }: { label: string; enabled?: boolean }) {
  return (
    <div className="row between">
      <span>{label}</span>
      <span className={`badge ${enabled ? "success" : ""}`}>{enabled ? "Enabled" : "Disabled"}</span>
    </div>
  );
}

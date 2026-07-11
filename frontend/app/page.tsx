"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Page from "@/components/Page";
import { api, formatDate } from "@/lib/api";

export default function Overview() {
  const [data, setData] = useState<any>();
  const [error, setError] = useState("");
  useEffect(() => { api("/api/overview").then(setData).catch(e => setError(e.message)); }, []);
  return <Page title="Overview" description="Operational knowledge, graph memory, and governed agent actions." action={<Link className="button" href="/ask">Ask Runbook</Link>}>
    {error && <div className="notice error">{error}</div>}
    <div className="grid metrics">
      {[["Projects", data?.projects], ["Knowledge items", data?.knowledge_items], ["Generated runbooks", data?.runbooks], ["Pending approvals", data?.pending_approvals]].map(([label, value]) => <div className="card metric" key={label}><div className="metric-label">{label}</div><div className="metric-value">{value ?? "—"}</div></div>)}
    </div>
    <div className="grid two">
      <section className="card"><div className="section-head"><h2>Graph memory</h2><span className={`badge ${data?.graph?.connected ? "success" : "danger"}`}>{data?.graph?.connected ? "Connected" : "Unavailable"}</span></div><div className="card-pad stack"><div className="row between"><span className="subtle">Backend</span><strong>{data?.graph?.backend || "arcadedb"}</strong></div><div className="row between"><span className="subtle">Database</span><strong>{data?.graph?.database || "runbook"}</strong></div><div className="row between"><span className="subtle">Connected sources</span><strong>{data?.connected_sources ?? "—"}</strong></div></div></section>
      <section className="card"><div className="section-head"><h2>Recent activity</h2><Link className="subtle" href="/audit">View audit log</Link></div><div className="card-pad">{data?.recent_activity?.length ? data.recent_activity.slice(0,5).map((item:any) => <div className="timeline-item" key={item.id}><h3>{item.summary}</h3><p className="subtle">{item.event_type} · {formatDate(item.created_at)}</p></div>) : <div className="empty">Activity appears after your first ingestion or query.</div>}</div></section>
    </div>
  </Page>;
}

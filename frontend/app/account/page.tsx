"use client";

import { useEffect, useState } from "react";
import Page from "@/components/Page";
import { api } from "@/lib/api";

export default function Account() {
  const [user, setUser] = useState<any>();
  const [error, setError] = useState("");
  useEffect(() => { api("/api/auth/me").then(setUser).catch(exc => setError(exc.message)); }, []);

  async function signOut() {
    await api("/api/auth/logout", {method:"POST"});
    localStorage.removeItem("runbook_token");
    window.location.assign("/login");
  }

  return <Page eyebrow="Identity" title="Account" description="Your identity, active workspace, and access boundary.">
    {error && <div className="notice error">{error}</div>}
    {user && <div className="account-layout">
      <section className="card card-pad stack"><div className="account-identity"><span>{user.display_name.split(/\s+/).map((part:string)=>part[0]).join("").slice(0,2).toUpperCase()}</span><div><h2>{user.display_name}</h2><p>{user.email}</p></div></div><div className="account-detail"><span>Identity provider</span><strong>{user.auth_provider}</strong></div><div className="account-detail"><span>Workspace role</span><strong>{user.role}</strong></div><button className="button secondary" onClick={signOut}>Sign out</button></section>
      <section className="card"><div className="section-head"><div><span className="panel-label">Workspace access</span><h2>Memberships</h2></div></div><div>{user.workspaces.map((workspace:any)=><div className="workspace-row" key={workspace.id}><div><strong>{workspace.name}</strong><small>{workspace.slug}</small></div><span className={`badge ${workspace.id === user.active_workspace_id ? "success" : ""}`}>{workspace.id === user.active_workspace_id ? "Active" : workspace.role}</span></div>)}</div></section>
    </div>}
  </Page>;
}

"use client";
import { useEffect, useState } from "react";
import Page from "@/components/Page";
import { API, api } from "@/lib/api";
export default function Connectors() {
  const [items, setItems] = useState<any[]>([]); const [provider, setProvider] = useState(""); const [token, setToken] = useState(""); const [message, setMessage] = useState("");
  const load = () => api<any[]>("/api/connectors").then(setItems);
  useEffect(() => { load(); }, []);
  async function save() { try { await api(`/api/connectors/${provider}/token`, {method:"POST", body: JSON.stringify({token})}); setMessage(`${provider} connected`); setToken(""); setProvider(""); load(); } catch(e:any) { setMessage(e.message); } }
  return <Page title="Connectors" description="Authorize source systems without exposing credentials to ingestion jobs.">
    {message && <div className={message.includes("connected") ? "notice" : "notice error"}>{message}</div>}
    <div className="grid three" style={{marginTop: message ? 16 : 0}}>{items.map(item => <div className="card connector" key={item.provider}><div className="row between"><div className="connector-logo">{item.provider.slice(0,2).toUpperCase()}</div><span className={`badge ${item.connected ? "success" : item.status === "planned" ? "" : "warning"}`}>{item.connected ? "Connected" : item.status === "planned" ? "Planned" : "Available"}</span></div><div><h2 style={{textTransform:"capitalize"}}>{item.provider.replace("_", " ")}</h2><p className="subtle">{item.connected ? `Authorized account${item.accounts?.length === 1 ? "" : "s"}: ${item.accounts?.map((a:any)=>a.display_name).join(", ")}` : item.status === "planned" ? "Connector architecture is ready for a future release." : "OAuth or secure local token connection."}</p></div>{item.available && !item.connected && <div className="row"><a className="button" href={`${API}/api/connectors/${item.provider}/auth/start`}>Connect with {item.provider === "github" ? "GitHub" : "Slack"}</a><button className="button secondary" onClick={()=>setProvider(item.provider)}>Use token</button></div>}</div>)}</div>
    {provider && <div className="card card-pad" style={{marginTop:16}}><div className="stack"><h2>Connect {provider} with a local token</h2><p className="subtle">The token is encrypted at rest and never returned by the API.</p><input type="password" value={token} onChange={e=>setToken(e.target.value)} placeholder={provider === "github" ? "github_pat_…" : "xoxb-…"}/><div className="row"><button className="button" onClick={save} disabled={!token}>Verify and connect</button><button className="button secondary" onClick={()=>setProvider("")}>Cancel</button></div></div></div>}
  </Page>;
}

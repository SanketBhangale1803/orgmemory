"use client";
import { useEffect, useState } from "react";
import Page from "@/components/Page";
import { api, formatDate } from "@/lib/api";
export default function Approvals(){
  const[items,setItems]=useState<any[]>([]); const[message,setMessage]=useState(""); const load=()=>api<any[]>("/api/actions").then(setItems);
  useEffect(()=>{load();},[]);
  async function resolve(id:string,approved:boolean){const r:any=await api(`/api/actions/${approved?"approve":"deny"}`,{method:"POST",body:JSON.stringify({action_id:id,resolved_by:"demo-user"})});setMessage(`Action ${r.status}. ${r.command_preview?`Command would execute in demo mode: ${r.command_preview}`:""}`);load();}
  return <Page title="Approvals" description="Human decisions for state-changing agent actions.">{message&&<div className="notice">{message}</div>}<div className="card" style={{marginTop:message?16:0}}>{items.length?<table className="table"><thead><tr><th>Action</th><th>Risk</th><th>Status</th><th>Requested</th><th>Decision</th></tr></thead><tbody>{items.map(item=><tr key={item.id}><td><strong>{item.summary}</strong><div className="subtle">{item.reason}</div>{item.command_preview&&<code>{item.command_preview}</code>}</td><td><span className={`badge ${item.risk_score>=80?"danger":"warning"}`}>{item.risk_score}/100</span></td><td><span className="badge">{item.status}</span></td><td>{formatDate(item.requested_at)}</td><td>{item.status==="pending"?<div className="row"><button className="button" onClick={()=>resolve(item.id,true)}>Approve</button><button className="button danger" onClick={()=>resolve(item.id,false)}>Deny</button></div>:<span className="subtle">{item.resolved_by||"—"}</span>}</td></tr>)}</tbody></table>:<div className="empty">No actions have been proposed.</div>}</div></Page>;
}

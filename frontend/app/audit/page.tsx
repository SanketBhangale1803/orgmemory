"use client";
import { useEffect, useState } from "react";
import Page from "@/components/Page";
import { api, formatDate } from "@/lib/api";
export default function Audit(){const[items,setItems]=useState<any[]>([]);useEffect(()=>{api<any[]>("/api/audit").then(setItems);},[]);return <Page title="Audit log" description="Immutable application history for ingestion, retrieval, extraction, and approvals."><div className="card">{items.length?<table className="table"><thead><tr><th>Event</th><th>Actor</th><th>Project</th><th>Time</th></tr></thead><tbody>{items.map(item=><tr key={item.id}><td><strong>{item.summary}</strong><div className="subtle">{item.event_type}</div></td><td>{item.actor}</td><td><code>{item.project_id||"workspace"}</code></td><td>{formatDate(item.created_at)}</td></tr>)}</tbody></table>:<div className="empty">Audit events appear here as the product is used.</div>}</div></Page>;}

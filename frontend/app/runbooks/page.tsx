"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Page from "@/components/Page";
import { api, formatDate } from "@/lib/api";
export default function Runbooks() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => { api<any[]>("/api/runbooks").then(setItems); }, []);
  return <Page title="Runbooks" description="Executable procedures extracted from cited operational evidence." action={<Link href="/ask" className="button">Extract runbook</Link>}><div className="grid three">{items.length ? items.map(item => <Link className="card card-pad stack" href={`/runbooks/${item.id}`} key={item.id}><div className="row between"><span className={`badge ${item.risk_level === "high" ? "danger" : item.risk_level === "medium" ? "warning" : "success"}`}>{item.risk_level} risk</span><span className="subtle">{Math.round(item.confidence * 100)}%</span></div><div><h2>{item.name}</h2><p className="subtle">{item.description}</p></div><div className="subtle">Updated {formatDate(item.updated_at)}</div></Link>) : <div className="card empty" style={{gridColumn:"1 / -1"}}>No runbooks extracted yet. Ask a grounded question, then extract the procedure.</div>}</div></Page>;
}

"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Page from "@/components/Page";
import { api, formatDate } from "@/lib/api";
export default function Projects() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => { api<any[]>("/api/projects").then(setItems); }, []);
  return <Page title="Projects" description="Repositories and operational knowledge isolated by project." action={<Link href="/ingest" className="button">New project</Link>}><div className="card">{items.length ? <table className="table"><thead><tr><th>Project</th><th>Repository</th><th>Knowledge</th><th>Runbooks</th><th>Created</th></tr></thead><tbody>{items.map(item => <tr key={item.id}><td><strong>{item.name}</strong><div className="subtle">{item.id}</div></td><td>{item.repository || "Uploaded knowledge"}</td><td>{item.knowledge_items}</td><td>{item.runbooks}</td><td>{formatDate(item.created_at)}</td></tr>)}</tbody></table> : <div className="empty">No projects yet. Ingest a repository or run <code>make demo</code>.</div>}</div></Page>;
}

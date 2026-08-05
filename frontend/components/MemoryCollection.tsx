"use client";

import { useEffect, useState } from "react";
import Page from "@/components/Page";
import { api } from "@/lib/api";

export default function MemoryCollection({title, description, endpoint, eyebrow="Company Memory"}:{title:string;description:string;endpoint:string;eyebrow?:string}) {
  const [projects,setProjects]=useState<any[]>([]); const [project,setProject]=useState("");
  const [items,setItems]=useState<any[]>([]); const [error,setError]=useState("");
  useEffect(()=>{api<any[]>("/api/projects").then(value=>{setProjects(value);if(value[0])setProject(value[0].id)}).catch(e=>setError(e.message))},[]);
  useEffect(()=>{if(!project)return;api<any>(`${endpoint}${endpoint.includes("?")?"&":"?"}project_id=${encodeURIComponent(project)}`).then(value=>setItems(Array.isArray(value)?value:Object.entries(value).map(([key,data])=>({key,data})))).catch(e=>setError(e.message))},[project,endpoint]);
  return <Page eyebrow={eyebrow} title={title} description={description} action={<select className="project-select" value={project} onChange={e=>setProject(e.target.value)}>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select>}>
    {error&&<div className="notice error">{error}</div>}
    <section className="panel"><div className="panel-head"><div><span className="panel-label">Live data</span><h2>{items.length} records</h2></div></div><div className="panel-body">{items.length?items.map((item,index)=><article className="clean-source-row" key={item.id||item.key||index}><span>{String(index+1).padStart(2,"0")}</span><div><div className="row between"><strong>{item.subject||item.relationship||item.key||item.name||item.node_type}</strong><small>{item.type||item.profile_type||"memory"}</small></div><p>{item.content||item.summary||item.data?.name||`${item.from_memory_id||""} ${item.relationship||""} ${item.to_memory_id||""}`}</p>{item.confidence!=null&&<small>{Math.round(item.confidence*100)}% extraction confidence · {item.is_latest?"current":"historical"}</small>}</div></article>):<div className="empty">No source-backed records yet. Connect or upload a source to build company memory.</div>}</div></section>
  </Page>;
}

"use client";

import { useEffect, useMemo, useState } from "react";
import Page from "@/components/Page";
import { api } from "@/lib/api";

type Project = { id: string; name: string };
type GraphSummary = {
  project_id: string;
  node_counts: Record<string, number>;
  edge_counts: Record<string, number>;
  total_nodes: number;
  total_edges: number;
  services: any[];
  files: any[];
};

export default function RepoGraph() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [summary, setSummary] = useState<GraphSummary | null>(null);
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [nodeType, setNodeType] = useState("");
  const [selectedService, setSelectedService] = useState("");
  const [serviceGraph, setServiceGraph] = useState<any | null>(null);
  const [radius, setRadius] = useState<any | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api<Project[]>("/api/projects").then((items) => {
      setProjects(items);
      if (items[0]) setProjectId(items[0].id);
    });
  }, []);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    setError("");
    Promise.all([
      api<GraphSummary>(`/api/projects/${projectId}/graph/summary`),
      api<any[]>(`/api/projects/${projectId}/graph/nodes?limit=300`),
      api<any[]>(`/api/projects/${projectId}/graph/edges?limit=300`),
    ])
      .then(([nextSummary, nextNodes, nextEdges]) => {
        setSummary(nextSummary);
        setNodes(nextNodes);
        setEdges(nextEdges);
        setSelectedService(nextSummary.services?.[0]?.name || "");
      })
      .catch((exc) => setError(exc.message))
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => {
    if (!projectId || !selectedService) {
      setServiceGraph(null);
      return;
    }
    api(`/api/projects/${projectId}/graph/service/${encodeURIComponent(selectedService)}`)
      .then(setServiceGraph)
      .catch(() => setServiceGraph(null));
    api(`/api/projects/${projectId}/graph/blast-radius/${encodeURIComponent(selectedService)}`)
      .then(setRadius)
      .catch(() => setRadius(null));
  }, [projectId, selectedService]);

  const filteredNodes = useMemo(
    () => nodes.filter((node) => !nodeType || node.node_type === nodeType),
    [nodes, nodeType],
  );
  const nodeTypes = Object.keys(summary?.node_counts || {}).sort();

  return (
    <Page
      title="Repo Graph"
      description="ArcadeDB-backed repository memory: files, services, issues, PRs, workflows, chunks, and evidence paths."
    >
      <div className="card card-pad stack">
        <div className="row between">
          <div className="field" style={{ maxWidth: 420 }}>
            <label>Project</label>
            <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>
          {loading && <span className="badge info">Loading graph</span>}
        </div>
        {error && <div className="notice error">{error}</div>}
      </div>

      {summary ? (
        <>
          <div className="grid metrics" style={{ marginTop: 18 }}>
            <Metric label="Graph nodes" value={summary.total_nodes} />
            <Metric label="Graph edges" value={summary.total_edges} />
            <Metric label="Services" value={summary.node_counts.Service || 0} />
            <Metric label="Files" value={summary.node_counts.File || 0} />
          </div>

          <div className="grid two">
            <section className="card">
              <div className="section-head">
                <h2>Graph Summary</h2>
                <span className="badge info">ArcadeDB</span>
              </div>
              <div className="card-pad graph-bars">
                {Object.entries(summary.node_counts).map(([type, count]) => (
                  <div className="bar-row" key={type}>
                    <span>{type}</span>
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${Math.max(6, (count / Math.max(summary.total_nodes, 1)) * 100)}%`,
                        }}
                      />
                    </div>
                    <strong>{count}</strong>
                  </div>
                ))}
              </div>
            </section>

            <section className="card">
              <div className="section-head">
                <h2>Service Map</h2>
                <span className="badge">{summary.services.length} services</span>
              </div>
              <div className="card-pad stack">
                <select
                  value={selectedService}
                  onChange={(event) => setSelectedService(event.target.value)}
                >
                  {summary.services.map((service) => (
                    <option key={service.id} value={service.name}>
                      {service.name}
                    </option>
                  ))}
                </select>
                {serviceGraph ? (
                  <div className="stack">
                    <div className="row between">
                      <span className="subtle">Connected edges</span>
                      <strong>{serviceGraph.edges?.length || 0}</strong>
                    </div>
                    <div className="row between">
                      <span className="subtle">Evidence chunks</span>
                      <strong>{serviceGraph.evidence?.length || 0}</strong>
                    </div>
                    {serviceGraph.evidence?.slice(0, 2).map((item: any) => (
                      <div className="source" key={item.chunk_id}>
                        <strong>{item.source_title}</strong>
                        <p>{item.snippet}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty">No service graph selected.</div>
                )}
              </div>
            </section>
          </div>

          {radius && (
            <section className="card" style={{ marginTop: 18 }}>
              <div className="section-head">
                <h2>Blast Radius — {radius.service_name}</h2>
                <span className="badge">graph edges only</span>
              </div>
              <div className="card-pad grid three">
                <div className="stack">
                  <h3>Depends on</h3>
                  {radius.dependencies.length ? (
                    radius.dependencies.map((name: string) => (
                      <span className="badge info" key={name}>{name}</span>
                    ))
                  ) : (
                    <p className="subtle">No dependency edges</p>
                  )}
                  <h3>Env vars</h3>
                  {radius.env_vars.length ? (
                    radius.env_vars.map((name: string) => <code key={name}>{name}</code>)
                  ) : (
                    <p className="subtle">No env var edges</p>
                  )}
                </div>
                <div className="stack">
                  <h3>Direct dependents</h3>
                  {radius.direct_dependents.length ? (
                    radius.direct_dependents.map((name: string) => (
                      <span className="badge warning" key={name}>{name}</span>
                    ))
                  ) : (
                    <p className="subtle">No dependent edges</p>
                  )}
                  <h3>Second hop</h3>
                  {radius.second_hop_dependents.length ? (
                    radius.second_hop_dependents.map((name: string) => (
                      <span className="badge" key={name}>{name}</span>
                    ))
                  ) : (
                    <p className="subtle">None</p>
                  )}
                </div>
                <div className="stack">
                  <h3>Impact</h3>
                  {radius.impact_statements.map((line: string) => (
                    <p className="subtle" key={line}>• {line}</p>
                  ))}
                </div>
              </div>
            </section>
          )}

          <div className="grid two" style={{ marginTop: 18 }}>
            <section className="card">
              <div className="section-head">
                <h2>File References</h2>
                <span className="badge">{summary.files.length} shown</span>
              </div>
              <table className="table">
                <thead>
                  <tr>
                    <th>Path</th>
                    <th>Language</th>
                    <th>Summary</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.files.slice(0, 12).map((file) => (
                    <tr key={file.id || file.path}>
                      <td>
                        <code>{file.path}</code>
                      </td>
                      <td>{file.language || "—"}</td>
                      <td>{file.summary || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className="card">
              <div className="section-head">
                <h2>Evidence Paths</h2>
                <span className="badge">{edges.length} edges</span>
              </div>
              <table className="table">
                <thead>
                  <tr>
                    <th>Relationship</th>
                    <th>From</th>
                    <th>To</th>
                  </tr>
                </thead>
                <tbody>
                  {edges.slice(0, 12).map((edge, index) => (
                    <tr key={`${edge.relationship}-${edge.from_id}-${edge.to_id}-${index}`}>
                      <td>{edge.relationship}</td>
                      <td>
                        <code>{edge.from_id}</code>
                      </td>
                      <td>
                        <code>{edge.to_id}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </div>

          <section className="card" style={{ marginTop: 18 }}>
            <div className="section-head">
              <h2>Graph Nodes</h2>
              <div className="row">
                <select value={nodeType} onChange={(event) => setNodeType(event.target.value)}>
                  <option value="">All node types</option>
                  {nodeTypes.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
                <span className="badge">{filteredNodes.length} nodes</span>
              </div>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>ID</th>
                  <th>Name / path</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {filteredNodes.slice(0, 80).map((node) => (
                  <tr key={`${node.node_type}-${node.id}`}>
                    <td>{node.node_type}</td>
                    <td>
                      <code>{node.id}</code>
                    </td>
                    <td>{node.name || node.path || node.source_title || node.route || "—"}</td>
                    <td className="subtle">{node.summary || node.command || node.pattern || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      ) : (
        <div className="empty">Ingest a repository to populate the graph explorer.</div>
      )}
    </Page>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <section className="card metric">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
    </section>
  );
}

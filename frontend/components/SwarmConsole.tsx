"use client";

import { useState } from "react";

const agents = [
  {
    id: "sensory",
    code: "01",
    name: "Sensory activation",
    role: "Hybrid recall",
    copy: "Semantic, lexical, and temporal signals activate the strongest source-backed memories.",
    result: "24 candidates · 18ms",
  },
  {
    id: "forager",
    code: "02",
    name: "Graph forager",
    role: "Bounded traversal",
    copy: "Query-matched entities seed a relationship walk that must terminate at exact evidence chunks.",
    result: "9 paths · 3 hops",
  },
  {
    id: "historian",
    code: "03",
    name: "Current-truth historian",
    role: "Temporal memory",
    copy: "Atomic memories are reconciled with updates, invalidations, authority, and current source versions.",
    result: "7 current facts · 0 stale",
  },
];

export default function SwarmConsole() {
  const [active, setActive] = useState(agents[0].id);
  const selected = agents.find((agent) => agent.id === active) || agents[0];

  return (
    <div className="swarm-console">
      <div className="swarm-console-top">
        <span><i /> activation_run_6f9a</span>
        <small>biological_context_swarm_v1</small>
      </div>
      <div className="swarm-console-body">
        <div className="swarm-agent-list" role="tablist" aria-label="Context activation agents">
          {agents.map((agent) => (
            <button
              aria-selected={agent.id === active}
              className={agent.id === active ? "active" : ""}
              key={agent.id}
              onClick={() => setActive(agent.id)}
              role="tab"
            >
              <span>{agent.code}</span>
              <div><strong>{agent.name}</strong><small>{agent.role}</small></div>
              <i />
            </button>
          ))}
        </div>
        <div className="swarm-agent-detail" role="tabpanel">
          <span className="om-kicker"><i /> Agent report</span>
          <h3>{selected.name}</h3>
          <p>{selected.copy}</p>
          <div className="agent-result"><small>RESULT</small><strong>{selected.result}</strong></div>
          <div className="agent-trace">
            <span>authorization_trimmed</span>
            <b>true</b>
            <span>status</span>
            <b>complete</b>
          </div>
        </div>
      </div>
      <div className="swarm-console-compiler">
        <span><i /> Critic</span><b>deduplicated · contradictions checked</b>
        <span><i /> Compiler</span><b>token-ready context emitted</b>
      </div>
    </div>
  );
}

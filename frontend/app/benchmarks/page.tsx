"use client";

import { useEffect, useState } from "react";
import Page from "@/components/Page";
import { api, formatDate } from "@/lib/api";

function MetricTable({ title, baseline, hcag }: { title: string; baseline: any; hcag: any }) {
  const keys = Object.keys(hcag || {}).filter(key => typeof hcag[key] === "number");
  if (!keys.length) return null;
  return <section className="card">
    <div className="section-head"><h2>{title}</h2></div>
    <div className="card-pad">
      <table className="table">
        <thead><tr><th>Metric</th><th>Baseline</th><th>HCAG</th><th>Δ</th></tr></thead>
        <tbody>{keys.map(key => {
          const base = baseline?.[key];
          const value = hcag[key];
          const delta = typeof base === "number" ? value - base : null;
          return <tr key={key}>
            <td>{key}</td>
            <td>{typeof base === "number" ? base.toFixed(3) : "—"}</td>
            <td>{value.toFixed(3)}</td>
            <td className={delta === null ? "" : delta >= 0 ? "positive" : "negative"}>{delta === null ? "—" : `${delta >= 0 ? "+" : ""}${delta.toFixed(3)}`}</td>
          </tr>;
        })}</tbody>
      </table>
    </div>
  </section>;
}

export default function Benchmarks() {
  const [data, setData] = useState<any>();
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/benchmarks").then(setData).catch(e => setError(e.message));
  }, []);

  return <Page title="Benchmark Reports" description="HCAG retrieval and routing benchmarks. Reports are produced only by running the real harness; if a number is missing, the run has not happened.">
    {error && <div className="notice error">{error}</div>}
    {!data && !error && <div className="card empty">Loading benchmark report…</div>}
    {data && !data.available && <div className="card empty">
      No benchmark report has been generated yet.<br/><br/>
      <code>cd ~/Desktop/startup/hcag && make benchmark</code><br/><br/>
      The harness runs a lexical baseline and the HCAG pipeline over the same labeled datasets and writes honest results to <code>benchmark_reports/latest.json</code>.
    </div>}
    {data?.available && <div className="stack">
      <section className="card card-pad row between">
        <div><div className="subtle">Generated</div><strong>{formatDate(data.report.generated_at)}</strong></div>
        <div><div className="subtle">Suites</div><strong>{Object.keys(data.report.suites || {}).length}</strong></div>
        <div><div className="subtle">Cases</div><strong>{data.report.total_cases}</strong></div>
        <div><div className="subtle">Verdict</div><span className={`badge ${data.report.hcag_beats_baseline ? "success" : "warning"}`}>{data.report.hcag_beats_baseline ? "HCAG beats baseline" : "Baseline not beaten everywhere"}</span></div>
      </section>
      {data.report.summary && <section className="card card-pad"><p className="answer">{data.report.summary}</p></section>}
      {Object.entries(data.report.suites || {}).map(([name, suite]: [string, any]) =>
        <MetricTable key={name} title={`${name} (${suite.cases} cases)`} baseline={suite.baseline} hcag={suite.hcag} />
      )}
      {(data.report.skipped || []).length > 0 && <section className="card card-pad stack">
        <h2>Skipped suites</h2>
        {data.report.skipped.map((item: any) => <p className="subtle" key={item.suite}>• {item.suite}: {item.reason}</p>)}
      </section>}
    </div>}
  </Page>;
}

# Benchmarks

Runbook's retrieval intelligence is benchmarked through HCAG's harness.

```bash
make benchmark        # from runbook/ — delegates to ../hcag
# or
cd ../hcag && make benchmark && make benchmark-report
```

Reports are written to `hcag/benchmark_reports/latest.{json,md}` and served
in the product at **Benchmark Reports** (`/benchmarks`, backed by
`GET /api/benchmarks`). If no report exists the page says so and shows the
command — it never displays fabricated numbers.

## What is measured

The harness compares a flat lexical baseline against the HCAG windowed
pipeline over the same committed labeled datasets with the same scorer, so
the delta isolates the routing/windowing layer. Suites:

- **multi_hop_incidents** — incident cause/config/ownership questions over
  a mixed-domain corpus with deliberate lexical distractors.
- **temporal_retrieval** — the temporally-correct memory must rank first.
- **company_brain_eval** — operational QA including unanswerable questions
  (abstention accuracy).
- **boundary_detection** — none/soft/hard transition F1 with the real
  `BoundaryDetector`.

Metrics: Recall@5, MRR, nDCG@5, evidence precision, answerability accuracy,
multi-hop success rate, temporal accuracy, boundary macro-F1, latency.

## Honesty rules

- Per-case retrievals ship inside `latest.json` for audit.
- `hcag_beats_baseline` is true only with zero regressed metrics.
- Regressions are listed by name when they happen.
- External suites (LoCoMo, LongMemEval, RepoQA) are reported as skipped
  with reasons when their datasets/API keys are absent.

See `hcag/docs/BENCHMARKS.md` for methodology detail and
`docs/HCAG_BENCHMARK_PLAN.md` for the plan and roadmap.

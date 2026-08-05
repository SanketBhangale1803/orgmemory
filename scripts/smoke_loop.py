#!/usr/bin/env python3
"""Drive the whole loop against a running backend and print what it learned.

    python scripts/smoke_loop.py --project prj_xxx --query "make the bg navy"

Ask -> handoff -> execute -> commit -> outcome recorded -> skill distilled.
Run it twice on the same query: the second run should carry a precedent.

Nothing here is mocked. It talks to the real API and makes a real commit on a
throwaway branch in a fresh clone, so the checkout you work in is never touched.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8000"
TERMINAL = {"committed", "pushed", "no_changes", "failed"}


def call(path: str, payload: dict | None = None, token: str = "") -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        f"{BASE}{path}", data=body, method="POST" if body else "GET"
    )
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Cookie", f"runbook_session={token}")
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return {"_error": exc.code, "_body": exc.read().decode()[:400]}
    except OSError as exc:
        return {"_error": 0, "_body": f"{exc} — is the backend running on {BASE}?"}


def die(message: str, detail: object = "") -> None:
    print(f"\n  ✗ {message}")
    if detail:
        print(f"    {detail}")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="project id, e.g. prj_abc123")
    parser.add_argument("--query", default="make the bg color navy blue")
    parser.add_argument("--executor", default="cursor", choices=("cursor", "claude"))
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--email", default="sanketbhangale3918@gmail.com")
    parser.add_argument(
        "--no-execute",
        action="store_true",
        help="stop after the handoff — no agent runs, no commit",
    )
    args = parser.parse_args()

    session = call("/api/auth/dev-login", {"email": args.email, "display_name": "Smoke"})
    if "_error" in session:
        die("could not log in", session.get("_body"))
    token = session["token"]

    for attempt in range(1, args.runs + 1):
        print(f"\n=== RUN {attempt}/{args.runs} ===")
        answer = call(
            "/api/ask",
            {
                "project_id": args.project,
                "query": args.query,
                "scope": "project",
                "surface": "script",
            },
            token,
        )
        if "_error" in answer:
            die("ask failed", answer.get("_body"))

        print(f"  scope     : {answer.get('answer_scope')}")
        print(f"  answer    : {(answer.get('answer') or '')[:100]}")

        if answer.get("clarification"):
            options = answer["clarification"].get("options", [])
            print("  → asked for clarification instead of guessing:")
            for option in options:
                print(f"      · {option.get('label')}")
            continue

        handoff = answer.get("handoff") or {}
        if not handoff:
            print("  → no handoff (this query was not read as an editor task)")
            continue

        precedents = handoff.get("precedents") or []
        print(f"  precedents: {len(precedents)}")
        for item in precedents:
            print(f"      · {item['trigger'][:60]} (worked {item['successes']}x)")
        print(f"  repository: {handoff.get('repository')}")

        if args.no_execute:
            continue

        started = call(
            "/api/execute",
            {
                "project_id": args.project,
                "handoff": handoff,
                "context_event_id": answer.get("context_event_id", ""),
                "executor": args.executor,
            },
            token,
        )
        if "_error" in started:
            die(f"execute rejected ({args.executor})", started.get("_body"))

        run = {}
        for _ in range(80):
            run = call(f"/api/execute/{started['id']}", token=token)
            if run.get("status") in TERMINAL:
                break
            time.sleep(6)

        print(f"  run       : {run.get('status')} {run.get('commit_sha', '')[:10]}")
        print(f"  files     : {run.get('files_changed')}")
        if run.get("error"):
            print(f"  error     : {run['error'][:200]}")

    print("\n=== LIBRARY ===")
    for skill in call("/api/skills/learned", token=token).get("skills", []):
        print(
            f"  [{skill['status']:8}] successes={skill['successes']} "
            f"failures={skill['failures']} confidence={skill['confidence']} "
            f":: {skill['trigger'][:50]}"
        )

    stats = call("/api/outcomes/stats", token=token)
    print("\n=== OUTCOMES ===")
    print(
        f"  contexts={stats.get('contexts')} actions={stats.get('actions')} "
        f"outcomes={stats.get('outcomes')} success_rate={stats.get('success_rate')}"
    )


if __name__ == "__main__":
    main()

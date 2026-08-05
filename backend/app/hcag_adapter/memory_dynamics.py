"""Ingestion-driven fast/slow evidence memory.

The state mirrors the two-timescale consolidation idea in Memini without
pretending that document chunks are neural synapses. Retrieval never mutates
this state: only a new source observation reinforces it. That keeps popularity
or repeated queries from turning an unsupported claim into company knowledge.
"""

from __future__ import annotations

from datetime import UTC, datetime
from math import exp
from typing import Any

from app.core.database import connect, row, utcnow

FAST_HALF_LIFE_DAYS = 14.0
SLOW_HALF_LIFE_DAYS = 180.0
FAST_INPUT = 0.58
SLOW_COUPLING = 0.14


def _parse_time(value: str | None, fallback: datetime) -> datetime:
    if not value:
        return fallback
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return fallback


def reinforce_memory(
    project_id: str,
    source_id: str,
    content_hash: str,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Reinforce a source version and return its inspectable memory state.

    Exact source versions consolidate with repeated observations. A changed
    version starts a fresh fast trace while inheriting only half of the prior
    source's slow signal, so updated evidence is immediately visible without
    erasing stable source history.
    """

    now = datetime.now(UTC)
    observed = _parse_time(observed_at, now)
    exact = row(
        "SELECT * FROM memory_dynamics WHERE project_id=? AND source_id=? AND content_hash=?",
        (project_id, source_id, content_hash),
    )
    previous = exact or row(
        "SELECT * FROM memory_dynamics WHERE project_id=? AND source_id=? "
        "ORDER BY updated_at DESC LIMIT 1",
        (project_id, source_id),
    )
    if previous:
        last = _parse_time(previous.get("last_reinforced_at"), observed)
        elapsed_days = max(0.0, (observed - last).total_seconds() / 86400.0)
        fast = float(previous.get("fast_weight") or 0.0) * exp(-elapsed_days / FAST_HALF_LIFE_DAYS)
        slow = float(previous.get("slow_weight") or 0.0) * exp(-elapsed_days / SLOW_HALF_LIFE_DAYS)
        if not exact:
            fast = 0.0
            slow *= 0.5
    else:
        fast = slow = 0.0

    fast = min(1.0, fast + FAST_INPUT)
    slow = min(1.0, slow + SLOW_COUPLING * fast)
    count = int((exact or {}).get("reinforcement_count") or 0) + 1
    first_seen = (exact or {}).get("first_seen_at") or observed.isoformat()
    updated = utcnow()
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO memory_dynamics "
            "(project_id,source_id,content_hash,fast_weight,slow_weight,reinforcement_count,"
            "first_seen_at,last_reinforced_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                project_id,
                source_id,
                content_hash,
                fast,
                slow,
                count,
                first_seen,
                observed.isoformat(),
                updated,
            ),
        )
    state = "consolidated" if slow >= 0.32 or count >= 3 else "recent"
    return {
        "fast_weight": round(fast, 4),
        "slow_weight": round(slow, 4),
        "reinforcement_count": count,
        "state": state,
        "last_reinforced_at": observed.isoformat(),
    }

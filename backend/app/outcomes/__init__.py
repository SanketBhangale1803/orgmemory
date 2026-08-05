"""The outcome loop: what context was served, what was done with it, what happened.

This package exists to accumulate the one asset that cannot be copied by a
competitor with a better model — a per-company record of which context actually
produced correct action. See :mod:`app.outcomes.ledger`.
"""

from .ledger import (
    OUTCOMES,
    export_training_records,
    record_action,
    record_context,
    record_outcome,
    stats,
)

__all__ = [
    "OUTCOMES",
    "export_training_records",
    "record_action",
    "record_context",
    "record_outcome",
    "stats",
]

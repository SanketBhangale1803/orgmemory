"""The answer surface shows answers, never the machinery behind them.

Ingested commit records are dense with labelled identifiers — SHAs, URLs,
timestamps. They rank well (short lines, full of query terms) and read as
gibberish: strings and numbers that mean nothing without the system that
produced them. Someone asking why something broke should never be handed one.
"""

from app.graph.base import GraphEvidence
from app.retrieval.universal import _answerable_line, universal_evidence_answer


def _evidence(chunk_id: str, title: str, text: str, score: float) -> GraphEvidence:
    return GraphEvidence(
        chunk_id=chunk_id,
        source_title=title,
        source_type="repo_file",
        source_url="",
        text=text,
        score=score,
        metadata={"path": title, "project_id": "p1"},
    )


COMMIT_RECORD = _evidence(
    "c2",
    "repository-metadata",
    "Latest commit message: theme changed\n"
    "Commit SHA: 77fde75fe032e03f332026acecc78b6802e42c8c\n"
    "Committed at: 2026-07-25T23:07:01Z\n"
    "URL: https://github.com/acme/widgets\n",
    # Deliberately outranks the README: metadata chunks score well because they
    # are short and dense with query terms. Filtering, not ranking, is the fix.
    95.0,
)
README = _evidence(
    "c1",
    "README.md",
    "# Widgets\n\nRun locally:\n\nnpm install\nnpm run dev\n\n"
    "The dev server listens on port 3000.\n",
    90.0,
)


def test_a_higher_ranked_commit_record_does_not_crowd_out_the_real_answer():
    answer = universal_evidence_answer("How do I run this locally?", [COMMIT_RECORD, README])

    assert answer["sufficient"]
    assert "npm run dev" in answer["answer"]
    assert "77fde75f" not in answer["answer"]
    assert "2026-07-25T23:07:01Z" not in answer["answer"]


def test_the_human_written_part_of_a_commit_record_still_answers():
    """Filtering machinery must not throw away what a person actually wrote."""
    answer = universal_evidence_answer("what changed recently?", [COMMIT_RECORD, README])

    assert answer["sufficient"]
    assert "theme changed" in answer["answer"]
    assert "77fde75f" not in answer["answer"]


def test_commit_machinery_is_never_quoted_as_an_answer():
    for line in [
        "Commit SHA: 77fde75fe032e03f332026acecc78b6802e42c8c",
        "Committed at: 2026-07-25T23:07:01Z",
        "URL: https://github.com/acme/widgets",
        "Latest commit URL: https://github.com/acme/widgets/commit/7b383d4b",
        "Author email: someone@example.com",
    ]:
        assert not _answerable_line(line), f"machinery leaked into an answer: {line}"


def test_sentences_that_happen_to_carry_a_label_still_answer():
    """The filter targets identifier-valued fields, not every colon.

    A commit *message* is what a human wrote about the change and is exactly what
    someone asking "what changed" wants; only the SHA beside it is machinery.
    """
    for line in [
        "Latest commit message: fixed the navy background on the login page",
        "Root cause: the worker was pointed at the old queue after the redeploy",
        "The deploy failed because the worker still pointed at the retired queue.",
    ]:
        assert _answerable_line(line), f"a real statement was filtered out: {line}"


def test_short_single_word_labels_remain_filtered_by_the_older_css_rule():
    """Documents a pre-existing limit rather than asserting it is right.

    `Label: value` with no inner colons is dropped by the rule that strips CSS
    declarations, so short prose fields are lost with them. Ownership questions
    have their own resolver, so this is a known edge rather than a live gap —
    but a future change to that rule should know it is load-bearing here.
    """
    assert not _answerable_line("Owner: the payments team")
    # A multi-word label sidesteps that rule entirely, which is why the behaviour
    # looks inconsistent from the outside.
    assert _answerable_line("Default branch: main")

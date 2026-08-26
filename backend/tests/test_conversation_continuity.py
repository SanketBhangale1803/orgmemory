"""A chat that forgets the previous turn is not a chat.

The failure these cover is not an error message — it is a confident answer about
the wrong subject, which is indistinguishable from knowledge.
"""

from app.audit import AuditService
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.retrieval import RetrievalService
from app.retrieval.continuity import resolve, unresolved_reference


def test_a_follow_up_is_bound_to_what_the_person_already_said():
    history = [
        {"role": "user", "content": "the checkout-api keeps returning 502"},
        {"role": "assistant", "content": "Here is what I found about that service."},
    ]

    resolved = resolve("why is it failing?", history)

    assert not resolved["dangling"]
    assert "checkout-api" in resolved["query"]
    assert "why is it failing?" in resolved["query"]


def test_a_dangling_reference_is_asked_about_rather_than_guessed_at():
    """Every corpus contains an incident, so guessing always finds one."""
    resolved = resolve("why is it failing?", [])

    assert resolved["dangling"]
    assert resolved["subject"] == ""


def test_a_question_that_names_its_own_subject_is_never_rewritten():
    history = [{"role": "user", "content": "tell me about the billing service"}]

    resolved = resolve("why is the checkout-api failing?", history)

    assert resolved["query"] == "why is the checkout-api failing?"
    assert resolved["subject"] == ""


def test_the_askers_own_words_win_over_the_assistants():
    """An assistant turn may wander onto a related file that was never the point."""
    history = [
        {"role": "user", "content": "the payments worker is stuck"},
        {"role": "assistant", "content": "The retry queue in redis_adapter.py looks relevant."},
    ]

    resolved = resolve("can you fix it", history)

    assert "payments" in resolved["query"]
    assert "redis_adapter" not in resolved["query"]


def test_a_thread_of_pronouns_does_not_anchor_to_another_pronoun():
    history = [
        {"role": "user", "content": "why is it broken"},
        {"role": "assistant", "content": "I need to know what you mean."},
    ]

    resolved = resolve("is it still broken?", history)

    assert resolved["dangling"], "a bare reference cannot anchor another one"


def test_stale_subjects_are_not_dragged_through_a_long_thread():
    history = [{"role": "user", "content": "the legacy importer crashed"}]
    history += [
        {"role": "user", "content": "how do I run the migration script"},
        {"role": "assistant", "content": "Use the make target."},
    ] * 4

    resolved = resolve("why did it fail", history)

    assert "legacy importer" not in resolved["query"]


def test_the_question_asked_back_names_the_word_it_could_not_resolve():
    asked = unresolved_reference("why is that failing?")

    assert "that" in asked["question"]
    assert asked["reason"] == "unresolved_reference"
    assert asked["options"], "asking without offering a way forward is a dead end"


def test_an_empty_or_plain_question_passes_through_untouched():
    assert resolve("what changed last week?", [])["query"] == "what changed last week?"
    assert resolve("", [])["query"] == ""
    assert not resolve("what changed last week?", [])["dangling"]


def _project(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Continuity")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "incidents/kafka.md",
        "The outage began after a Kafka redeploy advertised localhost:9092, "
        "which is unreachable from other containers.",
    )
    return hcag, project_id


def test_a_cold_open_pronoun_is_asked_about_instead_of_answered_from_any_incident(graph):
    """The bug this exists for: a corpus with one incident answers "why is it
    failing" with that incident, confidently, no matter what the asker meant."""
    hcag, project_id = _project(graph)

    result = RetrievalService(hcag).ask(project_id, "Why is it failing?", history=[])

    assert result["answer_scope"] == "clarification"
    assert result["clarification"]["reason"] == "unresolved_reference"
    assert "kafka" not in result["answer"].lower()


def test_the_same_question_is_answered_once_the_thread_supplies_a_subject(graph):
    hcag, project_id = _project(graph)

    result = RetrievalService(hcag).ask(
        project_id,
        "Why is it failing?",
        history=[{"role": "user", "content": "the kafka redeploy last night"}],
    )

    assert result["answer_scope"] != "clarification"
    assert result["resolved_subject"], "the binding must be visible, not silent"

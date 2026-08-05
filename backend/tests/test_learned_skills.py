"""Skills learned from verified outcomes — and the rules that keep them honest.

A library nobody curates becomes a garbage dump with great search, so most of
these tests are about what the library *refuses* to remember or keep.
"""

from app.skills import distil, list_skills, matches, record_use, retire

WORKSPACE = "wsp_skills"
PROJECT = "prj_skills"


def _worked(task: str, files: list[str], run_id: str = "run_1", commit: str = "abc123"):
    return distil(
        project_id=PROJECT,
        task=task,
        files=files,
        approach="1 file changed",
        workspace_id=WORKSPACE,
        run_id=run_id,
        commit_sha=commit,
    )


def test_a_verified_success_becomes_a_skill(graph):
    skill = _worked("change the background colour to navy", ["src/styles.css"])

    assert skill is not None
    assert skill["successes"] == 1
    assert skill["files"] == ["src/styles.css"]
    assert skill["commits"] == ["abc123"]


def test_one_success_is_a_coincidence_and_is_not_yet_trusted(graph):
    """A single lucky run must never be presented to an agent as precedent."""
    _worked("change the background colour to navy", ["src/styles.css"])

    assert matches(PROJECT, "change the background colour to navy") == []
    assert matches(PROJECT, "change the background colour to navy", trusted_only=False)


def test_a_second_success_is_what_earns_trust(graph):
    _worked("change the background colour to navy", ["src/styles.css"], run_id="run_1")
    skill = _worked("change the background colour to navy", ["src/styles.css"], run_id="run_2")

    assert skill["status"] == "active"
    assert skill["successes"] == 2
    assert [item["id"] for item in matches(PROJECT, "change the background colour")] == [
        skill["id"]
    ]


def test_similar_work_reinforces_rather_than_duplicating(graph):
    """Otherwise the library grows faster than it gets useful."""
    first = _worked("change the background colour to navy", ["src/styles.css"], run_id="run_1")
    second = _worked("change the background colour to navy", ["src/theme.css"], run_id="run_2")

    assert second["id"] == first["id"]
    assert len(list_skills(WORKSPACE)) == 1
    assert second["files"] == ["src/styles.css", "src/theme.css"]


def test_unrelated_work_is_kept_as_a_separate_skill(graph):
    _worked("change the background colour to navy", ["src/styles.css"])
    _worked("add rate limiting to the login endpoint", ["app/auth.py"])

    assert len(list_skills(WORKSPACE)) == 2


def test_a_skill_that_stops_working_retires_itself(graph):
    """The librarian's real job is pruning, and it should not need a human."""
    _worked("change the background colour to navy", ["src/styles.css"], run_id="run_1")
    skill = _worked("change the background colour to navy", ["src/styles.css"], run_id="run_2")
    assert skill["status"] == "active"

    record_use([skill["id"]], succeeded=False)
    record_use([skill["id"]], succeeded=False)
    record_use([skill["id"]], succeeded=False)

    retired = [item for item in list_skills(WORKSPACE) if item["id"] == skill["id"]][0]
    assert retired["status"] == "retired"
    assert "Failed 3 of 5" in retired["retired_reason"]
    assert matches(PROJECT, "change the background colour") == []


def test_confidence_never_claims_certainty_from_one_run(graph):
    skill = _worked("change the background colour to navy", ["src/styles.css"])

    assert 0.0 < skill["confidence"] < 1.0


def test_nothing_is_remembered_without_a_trigger_or_a_place(graph):
    assert _worked("", ["src/styles.css"]) is None
    assert _worked("change the background colour", []) is None


def test_a_reviewer_can_prune_by_hand(graph):
    _worked("change the background colour to navy", ["src/styles.css"], run_id="run_1")
    skill = _worked("change the background colour to navy", ["src/styles.css"], run_id="run_2")

    retire(skill["id"], "Superseded by the design system.")

    assert matches(PROJECT, "change the background colour") == []


def test_an_unrelated_question_matches_nothing(graph):
    _worked("change the background colour to navy", ["src/styles.css"], run_id="run_1")
    _worked("change the background colour to navy", ["src/styles.css"], run_id="run_2")

    assert matches(PROJECT, "who owns the billing service?") == []


def test_precedent_is_rendered_with_the_evidence_that_earned_it(graph):
    from app.skills import as_prompt_section

    _worked("change the background colour to navy", ["src/styles.css"], run_id="run_1")
    _worked("change the background colour to navy", ["src/styles.css"], run_id="run_2")

    section = as_prompt_section(matches(PROJECT, "change the background colour"))

    assert "worked 2 times" in section
    assert "src/styles.css" in section
    # Framed as precedent so an agent checks it rather than obeying it.
    assert "precedent, not instruction" in section

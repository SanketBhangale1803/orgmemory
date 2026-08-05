from __future__ import annotations

from orgmemory.cli import build_parser


def test_json_flag_works_after_subcommand() -> None:
    args = build_parser().parse_args(
        ["ask", "prj_platform", "What changed?", "--model", "gemini", "--json"]
    )
    assert args.command == "ask"
    assert args.json is True
    assert args.token_budget == 6000
    assert args.model == "gemini"


def test_ingest_file_arguments() -> None:
    args = build_parser().parse_args(
        [
            "ingest",
            "prj_platform",
            "--file",
            "incident.md",
            "--source-type",
            "incident",
        ]
    )
    assert args.file.name == "incident.md"
    assert args.source_type == "incident"

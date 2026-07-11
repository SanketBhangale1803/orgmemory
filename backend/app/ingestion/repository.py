from __future__ import annotations

import fnmatch
import hashlib
import shutil
from pathlib import Path
from typing import Any

from app.connectors.github import GitHubConnector
from app.core.config import settings
from app.core.database import connect, row, rows
from app.graph.base import GraphStore
from app.graph.graph_builder import RepoGraphBuilder

from .service import IngestionService

IGNORED_DIRS = {
    ".git",
    ".next",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
}
USEFUL_NAMES = {
    "readme.md",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "jenkinsfile",
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "go.mod",
    "cargo.toml",
    "makefile",
    ".env.example",
}
USEFUL_SUFFIXES = {
    ".md",
    ".txt",
    ".log",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".properties",
    ".xml",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".sh",
    ".sql",
    ".graphql",
    ".proto",
    ".vue",
    ".svelte",
    ".ejs",
    ".css",
}
EXCLUDED_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    "cookies.txt",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
}
SENSITIVE_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}
MAX_FILE_BYTES = 1_500_000
MAX_FILES = 5000


class RepositoryIngestor:
    def __init__(
        self, ingestion: IngestionService, graph: GraphStore, github: GitHubConnector | None = None
    ):
        self.ingestion = ingestion
        self.graph = graph
        self.github = github or GitHubConnector()
        self.graph_builder = RepoGraphBuilder(graph)

    def ingest(self, source: str, project_name: str) -> dict[str, Any]:
        existing = row("SELECT id FROM projects WHERE repository=?", (source,))
        project_id = self.ingestion.create_project(project_name, source)
        repository_id = f"repo:{project_id}"
        root, temporary = self._checkout(source, project_id)
        files_scanned = issues_scanned = pull_requests_scanned = chunks_created = 0
        graph_nodes_created = graph_edges_created = 0
        warnings: list[str] = []
        previous_files: dict[str, str] = {}
        current_files: dict[str, str] = {}
        try:
            if existing:
                previous_files = {
                    item["source_id"]: hashlib.sha256(
                        item["content"].encode("utf-8", errors="replace")
                    ).hexdigest()
                    for item in rows(
                        "SELECT source_id,content FROM knowledge_items WHERE project_id=? AND source_type='repo_file'",
                        (project_id,),
                    )
                }
                self.graph.clear_repository_knowledge(project_id)
                with connect() as conn:
                    conn.execute(
                        "DELETE FROM knowledge_items WHERE project_id=? AND source_type IN ('repo_file','github_issue','pull_request')",
                        (project_id,),
                    )
            for path in self._files(root):
                relative = path.relative_to(root).as_posix()
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                except OSError as exc:
                    warnings.append(f"Skipped {relative}: {exc}")
                    continue
                source_id = f"file:{project_id}:{relative}"
                content_hash = hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()
                current_files[source_id] = content_hash
                source_url = self._file_url(source, relative)
                graph_delta = self.graph_builder.build_file(
                    project_id,
                    repository_id,
                    root,
                    path,
                    relative,
                    content,
                    source_id,
                    source_url,
                )
                result = self.ingestion.ingest_item(
                    project_id,
                    "repo_file",
                    relative,
                    content,
                    source_url,
                    source_id,
                    {
                        "path": relative,
                        "size": path.stat().st_size,
                        "repository_id": repository_id,
                        "content_hash": content_hash,
                        "source_updated_at": path.stat().st_mtime,
                    },
                )
                graph_nodes_created += graph_delta["nodes_created"]
                graph_edges_created += graph_delta["edges_created"]
                files_scanned += 1
                chunks_created += result["chunks_created"]

            slug = self.github.slug(source)
            if slug and self.github.token():
                issues_scanned, issue_chunks = self._ingest_issues(slug, project_id, repository_id)
                pull_requests_scanned, pr_chunks = self._ingest_pull_requests(
                    slug, project_id, repository_id
                )
                chunks_created += issue_chunks + pr_chunks
            elif slug:
                warnings.append(
                    "Repository files were ingested. Connect GitHub to include issues and pull requests."
                )
        finally:
            if temporary:
                shutil.rmtree(root, ignore_errors=True)
        changed_files = sorted(
            source_id.removeprefix(f"file:{project_id}:")
            for source_id, previous_hash in previous_files.items()
            if current_files.get(source_id) != previous_hash
        )
        return {
            "project_id": project_id,
            "files_scanned": files_scanned,
            "issues_scanned": issues_scanned,
            "pull_requests_scanned": pull_requests_scanned,
            "knowledge_items_created": files_scanned + issues_scanned + pull_requests_scanned,
            "knowledge_chunks_created": chunks_created,
            "graph_nodes_created": graph_nodes_created,
            "graph_edges_created": graph_edges_created,
            "warnings": warnings,
            "change": {
                "type": "repository_reingestion",
                "ref": source,
                "changed_files": changed_files,
                "evidence": [
                    {
                        "kind": "repository_reingestion",
                        "file": path,
                        "detail": "File content hash changed between ingestions.",
                    }
                    for path in changed_files
                ],
            },
            "status": "success",
        }

    def _checkout(self, source: str, project_id: str) -> tuple[Path, bool]:
        expanded = Path(source).expanduser()
        if expanded.exists() and expanded.is_dir():
            return expanded.resolve(), False
        normalized = source.replace("\\", "/")
        if "/startup/" in normalized:
            relative = normalized.split("/startup/", 1)[1]
            mounted = settings.local_repo_mount / relative
            if mounted.exists() and mounted.is_dir():
                return mounted.resolve(), False
        mounted = settings.local_repo_mount / Path(source).name
        if not source.startswith(("http://", "https://", "git@")) and mounted.exists():
            return mounted.resolve(), False
        target = settings.repo_cache_dir / project_id
        target.parent.mkdir(parents=True, exist_ok=True)
        self.github.clone(source, target)
        return target, True

    def _files(self, root: Path):
        count = 0
        for path in sorted(root.rglob("*")):
            if count >= MAX_FILES:
                break
            if not path.is_file() or any(
                part in IGNORED_DIRS for part in path.relative_to(root).parts
            ):
                continue
            relative = path.relative_to(root).as_posix()
            lower = path.name.lower()
            if lower in EXCLUDED_FILES or path.suffix.lower() in SENSITIVE_SUFFIXES:
                continue
            in_docs_or_ci = relative.startswith(("docs/", ".github/workflows/"))
            config_like = any(
                fnmatch.fnmatch(lower, pattern)
                for pattern in ("*.config.*", "config.*", "*.service")
            )
            if not (
                lower in USEFUL_NAMES
                or path.suffix.lower() in USEFUL_SUFFIXES
                or in_docs_or_ci
                or config_like
            ):
                continue
            if path.stat().st_size > MAX_FILE_BYTES or b"\0" in path.read_bytes()[:2048]:
                continue
            count += 1
            yield path

    def _ingest_issues(self, slug: str, project_id: str, repository_id: str) -> tuple[int, int]:
        total = chunks = 0
        for issue in self.github.list_issues(slug):
            source_id = f"issue:{slug}:{issue['number']}"
            title = f"Issue #{issue['number']}: {issue['title']}"
            labels = ", ".join(label["name"] for label in issue.get("labels", []))
            content = f"{title}\nState: {issue.get('state')}\nLabels: {labels}\n\n{issue.get('body') or ''}"
            result = self.ingestion.ingest_item(
                project_id,
                "github_issue",
                title,
                content,
                issue["html_url"],
                source_id,
                {"number": issue["number"], "repository": slug},
            )
            self.graph.link("REPO_HAS_ISSUE", "Repository", repository_id, "Issue", source_id)
            total += 1
            chunks += result["chunks_created"]
        return total, chunks

    def _ingest_pull_requests(
        self, slug: str, project_id: str, repository_id: str
    ) -> tuple[int, int]:
        total = chunks = 0
        for pull in self.github.list_pull_requests(slug):
            source_id = f"pull:{slug}:{pull['number']}"
            title = f"Pull request #{pull['number']}: {pull['title']}"
            changed_files = self.github.pull_request_files(slug, int(pull["number"]))
            file_names = [
                item.get("filename", "") for item in changed_files if item.get("filename")
            ]
            head_sha = (pull.get("head") or {}).get("sha", "")
            content = f"{title}\nState: {pull.get('state')}\nCommit: {head_sha}\nChanged files: {', '.join(file_names)}\n\n{pull.get('body') or ''}"
            result = self.ingestion.ingest_item(
                project_id,
                "pull_request",
                title,
                content,
                pull["html_url"],
                source_id,
                {
                    "number": pull["number"],
                    "repository": slug,
                    "commit_sha": head_sha,
                    "changed_files": file_names,
                    "source_updated_at": pull.get("updated_at", ""),
                },
            )
            self.graph.link(
                "REPO_HAS_PULL_REQUEST", "Repository", repository_id, "PullRequest", source_id
            )
            for filename in file_names:
                self.graph.link(
                    "PR_TOUCHES_FILE",
                    "PullRequest",
                    source_id,
                    "File",
                    f"file:{project_id}:{filename}",
                )
            total += 1
            chunks += result["chunks_created"]
        return total, chunks

    @staticmethod
    def _file_url(source: str, relative: str) -> str:
        slug = GitHubConnector.slug(source)
        return (
            f"https://github.com/{slug}/blob/HEAD/{relative}"
            if slug
            else f"file://{Path(source).expanduser().resolve() / relative}"
        )

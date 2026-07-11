from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

from app.graph.base import GraphStore
from app.ingestion.extractors import extract_services, extract_signals

LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".sh": "Shell",
    ".sql": "SQL",
    ".md": "Markdown",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".css": "CSS",
    ".ejs": "EJS",
}


class RepoGraphBuilder:
    def __init__(self, graph: GraphStore):
        self.graph = graph

    def build_file(
        self,
        project_id: str,
        repository_id: str,
        root: Path,
        path: Path,
        relative: str,
        content: str,
        source_id: str,
        source_url: str,
    ) -> dict[str, int]:
        language = detect_language(path)
        signals = file_signals(relative, content)
        summary = summarize_file(relative, content, signals)
        stat = path.stat()
        file_payload = {
            "id": source_id,
            "project_id": project_id,
            "repository_id": repository_id,
            "path": relative,
            "filename": path.name,
            "extension": path.suffix.lower(),
            "language": language,
            "size": stat.st_size,
            "hash": hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest(),
            "last_modified": stat.st_mtime,
            "source_url": source_url,
            "summary": summary,
            "detected_services": signals["services"],
            "detected_imports": signals["imports"],
            "detected_env_vars": signals["env_vars"],
            "detected_commands": signals["commands"],
            "detected_urls": signals["urls"],
            "detected_errors": signals["errors"],
            "detected_configs": signals["config_keys"],
        }
        self.graph.upsert_file(file_payload)
        self.graph.link("REPO_HAS_FILE", "Repository", repository_id, "File", source_id)
        self._directories(project_id, repository_id, relative, source_id)
        self._language(project_id, source_id, language)
        self._services(project_id, source_id, signals)
        self._code_entities(project_id, source_id, signals)
        self._operational_signals(project_id, source_id, signals)
        self._package_dependencies(project_id, repository_id, relative, content)
        self._docker_compose(project_id, source_id, content)
        self._workflow(project_id, repository_id, source_id, relative, content)
        return {
            "nodes_created": 1
            + len(signals["services"])
            + len(signals["imports"])
            + len(signals["functions"])
            + len(signals["classes"])
            + len(signals["endpoints"])
            + len(signals["env_vars"])
            + len(signals["config_keys"])
            + len(signals["commands"])
            + len(signals["errors"]),
            "edges_created": 1
            + len(signals["services"])
            + len(signals["imports"])
            + len(signals["functions"])
            + len(signals["classes"])
            + len(signals["endpoints"])
            + len(signals["env_vars"])
            + len(signals["config_keys"])
            + len(signals["commands"])
            + len(signals["errors"]),
        }

    def _directories(
        self, project_id: str, repository_id: str, relative: str, file_id: str
    ) -> None:
        directory = str(Path(relative).parent)
        if directory == ".":
            directory = "/"
        directory_id = f"dir:{project_id}:{directory}"
        self.graph.upsert_node(
            "Directory",
            {
                "id": directory_id,
                "project_id": project_id,
                "path": directory,
                "name": "/" if directory == "/" else Path(directory).name,
            },
        )
        self.graph.link(
            "REPO_HAS_DIRECTORY", "Repository", repository_id, "Directory", directory_id
        )
        self.graph.link("DIRECTORY_HAS_FILE", "Directory", directory_id, "File", file_id)

    def _language(self, project_id: str, file_id: str, language: str) -> None:
        if language == "Unknown":
            return
        language_id = f"language:{language.lower()}"
        self.graph.upsert_node("Language", {"id": language_id, "name": language})
        self.graph.link("FILE_WRITTEN_IN_LANGUAGE", "File", file_id, "Language", language_id)

    def _services(self, project_id: str, file_id: str, signals: dict[str, list[str]]) -> None:
        for service in signals["services"]:
            service_id = f"{project_id}:{service}"
            self.graph.upsert_service({"id": service_id, "project_id": project_id, "name": service})
            self.graph.link("PROJECT_HAS_SERVICE", "Project", project_id, "Service", service_id)
            self.graph.link("FILE_MENTIONS_SERVICE", "File", file_id, "Service", service_id)
            if signals.get("defines_service"):
                self.graph.link("SERVICE_DEFINED_IN_FILE", "Service", service_id, "File", file_id)
        for env_var in signals["env_vars"]:
            env_id = f"env:{project_id}:{env_var}"
            self.graph.upsert_node(
                "EnvironmentVariable",
                {"id": env_id, "project_id": project_id, "name": env_var},
            )
            self.graph.link(
                "FILE_REFERENCES_ENV_VAR", "File", file_id, "EnvironmentVariable", env_id
            )
            for service in signals["services"]:
                self.graph.link(
                    "SERVICE_USES_ENV_VAR",
                    "Service",
                    f"{project_id}:{service}",
                    "EnvironmentVariable",
                    env_id,
                )

    def _code_entities(self, project_id: str, file_id: str, signals: dict[str, list[str]]) -> None:
        for module in signals["imports"]:
            module_id = f"import:{project_id}:{module}"
            self.graph.upsert_node(
                "Import", {"id": module_id, "project_id": project_id, "name": module}
            )
            self.graph.link("FILE_IMPORTS_MODULE", "File", file_id, "Import", module_id)
        for name in signals["functions"]:
            function_id = f"function:{file_id}:{name}"
            self.graph.upsert_node(
                "Function", {"id": function_id, "project_id": project_id, "name": name}
            )
            self.graph.link("FILE_DEFINES_FUNCTION", "File", file_id, "Function", function_id)
        for name in signals["classes"]:
            class_id = f"class:{file_id}:{name}"
            self.graph.upsert_node(
                "Class", {"id": class_id, "project_id": project_id, "name": name}
            )
            self.graph.link("FILE_DEFINES_CLASS", "File", file_id, "Class", class_id)
        for endpoint in signals["endpoints"]:
            endpoint_id = f"endpoint:{file_id}:{endpoint}"
            self.graph.upsert_node(
                "Endpoint", {"id": endpoint_id, "project_id": project_id, "route": endpoint}
            )
            self.graph.link("FILE_DEFINES_ENDPOINT", "File", file_id, "Endpoint", endpoint_id)

    def _operational_signals(
        self, project_id: str, file_id: str, signals: dict[str, list[str]]
    ) -> None:
        for key in signals["config_keys"]:
            config_id = f"config:{project_id}:{key}"
            self.graph.upsert_node(
                "ConfigKey", {"id": config_id, "project_id": project_id, "name": key}
            )
            self.graph.link("FILE_REFERENCES_CONFIG_KEY", "File", file_id, "ConfigKey", config_id)
        for command in signals["commands"]:
            command_id = f"command:{file_id}:{stable_suffix(command)}"
            self.graph.upsert_node(
                "Command", {"id": command_id, "project_id": project_id, "command": command}
            )
            self.graph.link("STEP_RUNS_COMMAND", "File", file_id, "Command", command_id)
        for error in signals["errors"]:
            error_id = f"error:{project_id}:{stable_suffix(error)}"
            self.graph.upsert_node(
                "ErrorPattern", {"id": error_id, "project_id": project_id, "pattern": error}
            )
            self.graph.link("LOG_CONTAINS_ERROR_PATTERN", "File", file_id, "ErrorPattern", error_id)

    def _package_dependencies(
        self, project_id: str, repository_id: str, relative: str, content: str
    ) -> None:
        if Path(relative).name != "package.json":
            return
        try:
            package = json.loads(content)
        except json.JSONDecodeError:
            return
        package_id = f"package:{project_id}:{package.get('name') or 'package.json'}"
        self.graph.upsert_node(
            "Package",
            {
                "id": package_id,
                "project_id": project_id,
                "name": package.get("name", "package.json"),
                "version": package.get("version", ""),
            },
        )
        self.graph.link("REPO_HAS_DIRECTORY", "Repository", repository_id, "Package", package_id)
        deps = dict(package.get("dependencies") or {})
        deps.update(package.get("devDependencies") or {})
        for name, _version in sorted(deps.items())[:250]:
            dependency_id = f"dependency:{name}"
            self.graph.upsert_node("Dependency", {"id": dependency_id, "name": name})
            self.graph.link(
                "PACKAGE_HAS_DEPENDENCY", "Package", package_id, "Dependency", dependency_id
            )

    def _docker_compose(self, project_id: str, file_id: str, content: str) -> None:
        if "services:" not in content[:5000]:
            return
        try:
            parsed = yaml.safe_load(content) or {}
        except yaml.YAMLError:
            return
        for name, config in (parsed.get("services") or {}).items():
            docker_id = f"docker:{project_id}:{name}"
            service_id = f"{project_id}:{normalize_service(name)}"
            depends = sorted((config or {}).get("depends_on") or [])
            env = config.get("environment") or {}
            if isinstance(env, list):
                env_names = [str(value).split("=", 1)[0] for value in env]
            else:
                env_names = list(env.keys())
            self.graph.upsert_node(
                "DockerService",
                {
                    "id": docker_id,
                    "project_id": project_id,
                    "name": name,
                    "image": (config or {}).get("image", ""),
                    "ports": (config or {}).get("ports", []),
                    "depends_on": depends,
                    "environment": env_names,
                },
            )
            self.graph.upsert_service(
                {"id": service_id, "project_id": project_id, "name": normalize_service(name)}
            )
            self.graph.link(
                "SERVICE_HAS_DOCKER_CONFIG", "Service", service_id, "DockerService", docker_id
            )
            self.graph.link("FILE_MENTIONS_SERVICE", "File", file_id, "Service", service_id)
            for dep in depends:
                self.graph.link(
                    "SERVICE_DEPENDS_ON_SERVICE",
                    "Service",
                    service_id,
                    "Service",
                    f"{project_id}:{normalize_service(str(dep))}",
                )

    def _workflow(
        self, project_id: str, repository_id: str, file_id: str, relative: str, content: str
    ) -> None:
        lower = relative.lower()
        if not (
            lower.startswith(".github/workflows/") or Path(relative).name.lower() == "jenkinsfile"
        ):
            return
        workflow_id = f"workflow:{project_id}:{relative}"
        self.graph.upsert_node(
            "Workflow",
            {
                "id": workflow_id,
                "project_id": project_id,
                "name": Path(relative).name,
                "path": relative,
            },
        )
        self.graph.link("REPO_HAS_WORKFLOW", "Repository", repository_id, "Workflow", workflow_id)
        self.graph.link("DIRECTORY_HAS_FILE", "Workflow", workflow_id, "File", file_id)
        for index, command in enumerate(file_signals(relative, content)["commands"]):
            step_id = f"step:{workflow_id}:{index}"
            command_id = f"command:{workflow_id}:{stable_suffix(command)}"
            self.graph.upsert_node(
                "Step", {"id": step_id, "project_id": project_id, "name": f"step {index + 1}"}
            )
            self.graph.upsert_node(
                "Command", {"id": command_id, "project_id": project_id, "command": command}
            )
            self.graph.link("WORKFLOW_HAS_JOB", "Workflow", workflow_id, "Step", step_id)
            self.graph.link("STEP_RUNS_COMMAND", "Step", step_id, "Command", command_id)


def detect_language(path: Path) -> str:
    if path.name.lower() == "dockerfile":
        return "Dockerfile"
    if path.name.lower() == "jenkinsfile":
        return "Jenkinsfile"
    return LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "Unknown")


def file_signals(relative: str, content: str) -> dict[str, list[str] | bool]:
    extracted = extract_signals(content)
    services = extract_services(content, relative)
    imports = sorted(set(_python_imports(content) + _js_imports(content)))[:200]
    functions = sorted(set(re.findall(r"(?m)^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(", content)))
    functions += sorted(set(re.findall(r"\bfunction\s+([A-Za-z_]\w*)\s*\(", content)))
    functions += sorted(
        set(re.findall(r"\b(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*(?:async\s*)?\(", content))
    )
    classes = sorted(set(re.findall(r"(?m)^\s*class\s+([A-Za-z_]\w*)", content)))[:200]
    endpoints = sorted(
        set(
            re.findall(r"@\w+\.(?:get|post|put|patch|delete)\(['\"]([^'\"]+)", content)
            + re.findall(
                r"\b(?:app|router)\.(?:get|post|put|patch|delete)\(['\"]([^'\"]+)", content
            )
        )
    )[:200]
    env_vars = sorted(
        set(
            re.findall(r"\b(?:os\.getenv|os\.environ\.get)\(['\"]([A-Z][A-Z0-9_]{2,})", content)
            + re.findall(r"\bprocess\.env\.([A-Z][A-Z0-9_]{2,})", content)
            + re.findall(r"\$\{([A-Z][A-Z0-9_]{2,})\}", content)
        )
    )[:200]
    config_keys = sorted(
        set(re.findall(r"(?m)^\s*([A-Za-z][A-Za-z0-9_.-]{2,})\s*[:=]\s*[^:\n]+$", content))
    )[:200]
    urls = sorted(set(re.findall(r"https?://[^\s)'\"<>]+", content)))[:100]
    return {
        "services": services,
        "imports": imports,
        "functions": functions[:200],
        "classes": classes,
        "endpoints": endpoints,
        "env_vars": env_vars,
        "config_keys": config_keys,
        "commands": extracted["commands"],
        "errors": extracted["errors"],
        "procedures": extracted["procedures"],
        "urls": urls,
        "defines_service": bool(Path(relative).stem.lower() in set(services)),
    }


def _python_imports(content: str) -> list[str]:
    modules: list[str] = []
    modules.extend(re.findall(r"(?m)^\s*import\s+([A-Za-z_][\w.]*)(?:\s+as\s+\w+)?", content))
    modules.extend(re.findall(r"(?m)^\s*from\s+([A-Za-z_][\w.]*)\s+import\s+", content))
    return modules


def _js_imports(content: str) -> list[str]:
    modules = re.findall(r"\bfrom\s+['\"]([^'\"]+)['\"]", content)
    modules.extend(re.findall(r"\brequire\(['\"]([^'\"]+)['\"]\)", content))
    return modules


def summarize_file(relative: str, content: str, signals: dict[str, Any]) -> str:
    first_heading = re.search(r"(?m)^#\s+(.+)$", content)
    if first_heading:
        return first_heading.group(1)[:240]
    if signals["functions"] or signals["classes"]:
        return (
            f"{relative} defines " + ", ".join((signals["classes"] + signals["functions"])[:5])
        )[:240]
    first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
    return first_line[:240]


def normalize_service(value: str) -> str:
    value = value.lower().replace("-", "_")
    return value if value.endswith("_service") or value in {"kafka", "redis", "postgres"} else value


def stable_suffix(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="replace")).hexdigest()[:16]

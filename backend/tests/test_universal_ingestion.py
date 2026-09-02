"""Universal ingestion: documents (PDF/DOCX/XLSX/PPTX/HTML/RTF/EML), website
fetching, and the connector platform additions (Notion, Google Drive, Teams,
custom REST sources).

The extraction tests build minimal OOXML/OpenDocument zip containers inline so
no binary fixtures are needed. Connector tests stub the transport layer so the
suite stays hermetic.
"""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth.app_auth import create_workspace
from app.connectors.base import ConnectorAccount
from app.connectors.google_drive.client import GoogleDriveConnector
from app.connectors.notion.client import NotionConnector
from app.connectors.registry import get_connector_registry
from app.connectors.rest_pull import RestPullConnector
from app.connectors.teams.client import TeamsConnector
from app.ingestion.documents import (
    MAX_SOURCE_BYTES,
    UnsupportedDocumentError,
    extract_document,
)
from app.main import app

# ---------------------------------------------------------------------------
# OOXML / OpenDocument fixtures
# ---------------------------------------------------------------------------


def _build_docx(paragraphs: list[tuple[str, str]], table_rows: list[list[str]]) -> bytes:
    body_parts = []
    for style, text in paragraphs:
        ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        body_parts.append(f"<w:p>{ppr}<w:r><w:t>{text}</w:t></w:r></w:p>")
    if table_rows:
        rows = "".join(
            "<w:tr>"
            + "".join(f"<w:tc><w:p><w:r><w:t>{cell}</w:t></w:r></w:p></w:tc>" for cell in row)
            + "</w:tr>"
            for row in table_rows
        )
        body_parts.append(f"<w:tbl><w:tblPr/><w:tblGrid/>{rows}</w:tbl>")
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(body_parts)}</w:body></w:document>"
    )
    core = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Runbook Draft</dc:title></cp:coreProperties>'
    )
    content_types = (
        '<?xml version="1.0"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("docProps/core.xml", core)
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def _build_xlsx(sheets: list[tuple[str, list[list[str]]]]) -> bytes:
    content_types = (
        '<?xml version="1.0"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        "</Types>"
    )
    workbook_sheets = "".join(
        f'<sheet name="{name}" sheetId="{index + 1}" '
        f'r:id="rId{index + 1}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>'
        for index, (name, _) in enumerate(sheets)
    )
    workbook = (
        '<?xml version="1.0"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheets>{workbook_sheets}</sheets></workbook>"
    )
    rels = (
        '<?xml version="1.0"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="rId{index + 1}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index + 1}.xml"/>'
            for index in range(len(sheets))
        )
        + "</Relationships>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        for index, (_, rows) in enumerate(sheets):
            sheet_rows = "".join(
                "<row>"
                + "".join(
                    f'<c r="{"ABCDE"[cell_index]}{row_index + 1}" t="inlineStr">'
                    f"<is><t>{value}</t></is></c>"
                    for cell_index, value in enumerate(row)
                )
                + "</row>"
                for row_index, row in enumerate(rows)
            )
            archive.writestr(
                f"xl/worksheets/sheet{index + 1}.xml",
                '<?xml version="1.0"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f"{sheet_rows}</worksheet>",
            )
    return buffer.getvalue()


def _build_pptx(slides: list[list[str]]) -> bytes:
    content_types = (
        '<?xml version="1.0"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
        "</Types>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        for index, lines in enumerate(slides, start=1):
            paragraphs = "".join(
                f"<a:p><a:r><a:t>{line}</a:t></a:r></a:p>" "<a:p><a:r><a:t>filler</a:t></a:r></a:p>"
                for line in lines
            )
            archive.writestr(
                f"ppt/slides/slide{index}.xml",
                '<?xml version="1.0"?>'
                '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                f"<p:txBody>{paragraphs}</p:txBody></p:sld>",
            )
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Document extraction
# ---------------------------------------------------------------------------


def test_docx_extraction_preserves_headings_tables_and_title():
    data = _build_docx(
        [
            ("Heading1", "Deployment steps"),
            ("", "Roll out canary to 5 percent of traffic first."),
            ("Heading2", "Rollback"),
        ],
        [["service", "owner"], ["payments", "infra-team"]],
    )
    document = extract_document("runbook.docx", data)
    assert document.format == "docx"
    assert document.title == "Runbook Draft"
    assert "# Deployment steps" in document.text
    assert "## Rollback" in document.text
    assert "| service | owner |" in document.text
    assert "| payments | infra-team |" in document.text


def test_xlsx_extraction_reads_sheets_and_values():
    data = _build_xlsx(
        [
            ("On-call", [["engineer", "week"], ["ada", "2026-W36"], ["grace", "2026-W37"]]),
            ("Contacts", [["team", "email"], ["infra", "infra@example.com"]]),
        ]
    )
    document = extract_document("schedule.xlsx", data)
    assert document.format == "xlsx"
    assert "## Sheet: On-call" in document.text
    assert "## Sheet: Contacts" in document.text
    assert "ada | 2026-W36" in document.text
    assert "infra@example.com" in document.text


def test_pptx_extraction_orders_slides_and_notes():
    data = _build_pptx([["Incident review", "payments"], ["Root cause", "pool exhaustion"]])
    document = extract_document("review.pptx", data)
    assert document.format == "pptx"
    assert document.metadata["slide_count"] == 2
    assert document.text.index("## Slide 1") < document.text.index("## Slide 2")
    assert "**Incident review**" in document.text
    assert "pool exhaustion" in document.text


def test_html_extraction_drops_scripts_and_keeps_text():
    html = (
        "<html><head><title>Status</title>"
        "<style>body { color: red }</style></head><body>"
        "<script>alert(1)</script>"
        "<h1>Payments Status</h1><p>All clear <b>since</b> 09:00 UTC.</p>"
        "</body></html>"
    )
    document = extract_document("status.html", html.encode())
    assert document.format == "html"
    assert document.title == "Status"
    assert "alert(1)" not in document.text
    assert "color: red" not in document.text
    assert "# Payments Status" in document.text
    assert "All clear since 09:00 UTC." in document.text


def test_rtf_extraction_strips_control_words():
    rtf = (
        r"{\rtf1\ansi{\fonttbl{\f0 Helvetica;}}\f0\fs28"
        r"\par Escalate to \b SRE on-call\b0 \par Page via PD \par}"
    )
    document = extract_document("escalation.rtf", rtf.encode())
    assert document.format == "rtf"
    assert "fonttbl" not in document.text
    assert "Escalate to SRE on-call" in document.text


def test_eml_extraction_includes_headers_and_body():
    eml = (
        "From: ada@example.com\r\n"
        "To: team@example.com\r\n"
        "Subject: Payments degraded\r\n"
        "Date: Mon, 1 Sep 2026 10:00:00 +0000\r\n"
        "Content-Type: text/plain\r\n\r\n"
        "Pool exhaustion recurred during the batch job.\r\n"
    )
    document = extract_document("incident.eml", eml.encode())
    assert document.format == "eml"
    assert document.title == "Payments degraded"
    assert "Pool exhaustion recurred" in document.text
    assert "ada@example.com" in document.text


def test_pdf_extraction_reports_pages_and_image_only_warning():
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    document = extract_document("scan.pdf", buffer.getvalue())
    assert document.format == "pdf"
    assert document.metadata["page_count"] == 1
    assert "No text layer" in " ".join(document.warnings)


def test_content_sniffing_recovers_office_files_with_wrong_extension():
    data = _build_docx([("", "still readable")], [])
    document = extract_document("export.bin", data)
    assert document.format == "docx"
    assert "still readable" in document.text


def test_empty_and_oversized_files_are_rejected():
    with pytest.raises(UnsupportedDocumentError):
        extract_document("empty.md", b"")
    original_limit = MAX_SOURCE_BYTES
    try:
        import app.ingestion.documents as documents

        documents.MAX_SOURCE_BYTES = 8
        with pytest.raises(UnsupportedDocumentError):
            extract_document("big.md", b"x" * 64)
    finally:
        import app.ingestion.documents as documents

        documents.MAX_SOURCE_BYTES = original_limit


# ---------------------------------------------------------------------------
# Website ingestion endpoint
# ---------------------------------------------------------------------------


def _workspace_and_project(client: TestClient) -> tuple[str, str, dict]:
    login = client.post(
        "/api/auth/dev-login",
        json={"email": "web-ingest@example.com", "display_name": "Web Ingest"},
    )
    token = login.json()["token"]
    workspace = create_workspace("Web Ingest Workspace", f"Bearer {token}")
    project = client.post(
        "/api/projects",
        json={"name": "Website project"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    return token, project["id"], workspace


def test_website_ingestion_endpoint_ingests_page_text(graph, monkeypatch):
    from app.ingestion import web as web_module
    from app.ingestion.documents import ExtractedDocument

    def fake_fetch(url: str):
        document = ExtractedDocument(
            text="# Payments runbook\n\nRestart the workers before scaling the pool.",
            format="html",
            title="Payments runbook",
            metadata={"format": "html"},
        )
        return document, {
            "requested_url": url,
            "final_url": "https://docs.example.com/payments",
            "http_status": 200,
            "content_type": "text/html",
            "fetched_at": "2026-09-02T00:00:00+00:00",
        }

    monkeypatch.setattr(web_module, "fetch_web_document", fake_fetch)
    monkeypatch.setattr("app.api.routes.fetch_web_document", fake_fetch)
    with TestClient(app) as client:
        token, project_id, _ = _workspace_and_project(client)
        response = client.post(
            "/api/ingest/website",
            json={"project_id": project_id, "url": "docs.example.com/payments"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "success"
        assert payload["chunks_created"] >= 1
        assert payload["final_url"] == "https://docs.example.com/payments"
        answer = client.post(
            "/api/ask",
            json={"project_id": project_id, "query": "how do I scale payments safely?"},
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert answer.get("evidence"), "ingested page should be retrievable"


def test_website_ingestion_rejects_private_targets(graph, monkeypatch):
    from app.ingestion.web import WebFetchError

    def refuse(url: str):
        raise WebFetchError("Web ingestion cannot target private or special-use addresses")

    monkeypatch.setattr("app.api.routes.fetch_web_document", refuse)
    with TestClient(app) as client:
        token, project_id, _ = _workspace_and_project(client)
        response = client.post(
            "/api/ingest/website",
            json={"project_id": project_id, "url": "https://127.0.0.1:8080/secret"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "private" in response.json()["detail"]


def test_web_fetcher_resolves_and_rejects_loopback(monkeypatch):
    from app.ingestion.web import WebFetchError, _validate_public_url

    with pytest.raises(WebFetchError):
        _validate_public_url("http://127.0.0.1:8080/admin")
    with pytest.raises(WebFetchError):
        _validate_public_url("ftp://example.com/file")
    with pytest.raises(WebFetchError):
        _validate_public_url("https://user:pass@example.com/file")
    assert _validate_public_url("https://example.com/ok") == "https://example.com/ok"


# ---------------------------------------------------------------------------
# File upload endpoint with real document formats
# ---------------------------------------------------------------------------


def test_file_upload_accepts_docx_and_becomes_retrievable(graph):
    with TestClient(app) as client:
        token, project_id, _ = _workspace_and_project(client)
        data = _build_docx(
            [("Heading1", "Payments escalation"), ("", "Page the SRE on-call first.")], []
        )
        response = client.post(
            "/api/ingest/file",
            data={"project_id": project_id, "source_type": "doc"},
            files={
                "file": (
                    "escalation.docx",
                    data,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["format"] == "docx"
        assert payload["chunks_created"] >= 1
        answer = client.post(
            "/api/ask",
            json={"project_id": project_id, "query": "who do I page for payments?"},
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert answer.get("evidence")


def test_file_upload_rejects_unknown_binary_type(graph):
    with TestClient(app) as client:
        token, project_id, _ = _workspace_and_project(client)
        response = client.post(
            "/api/ingest/file",
            data={"project_id": project_id},
            files={"file": ("payload.exe", b"MZ\x90\x00", "application/octet-stream")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 415


# ---------------------------------------------------------------------------
# Built-in connector registration
# ---------------------------------------------------------------------------


def test_new_builtin_connectors_register_with_verified_manifests():
    registry = get_connector_registry()
    providers = {manifest.id for manifest in registry.manifests()}
    assert {"github", "slack", "notion", "google_drive", "teams"} <= providers


class _StubResponse:
    def __init__(self, payload: Any, status_code: int = 200, headers: dict | None = None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.content = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.text = self.content.decode("utf-8", "replace")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)

    def json(self) -> Any:
        return self._payload


def test_notion_sync_turns_pages_and_databases_into_records(monkeypatch):
    search_payload = {
        "results": [
            {
                "object": "page",
                "id": "page-1",
                "url": "https://notion.so/page-1",
                "last_edited_time": "2026-09-01T00:00:00.000Z",
                "properties": {"title": {"type": "title", "title": [{"plain_text": "Runbook"}]}},
            },
            {
                "object": "database",
                "id": "db-1",
                "url": "https://notion.so/db-1",
                "title": [{"plain_text": "Owners"}],
                "properties": {},
            },
        ],
        "has_more": False,
        "next_cursor": None,
    }
    blocks_payload = {
        "results": [
            {
                "id": "b1",
                "type": "heading_1",
                "heading_1": {"rich_text": [{"plain_text": "Escalation"}], "has_children": False},
            },
            {
                "id": "b2",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"plain_text": "Page the on-call"}],
                    "has_children": False,
                },
            },
        ],
        "has_more": False,
        "next_cursor": None,
    }
    query_payload = {
        "results": [
            {
                "id": "row-1",
                "url": "https://notion.so/row-1",
                "last_edited_time": "2026-09-01T02:00:00.000Z",
                "properties": {
                    "Name": {"type": "title", "title": [{"plain_text": "Payments"}]},
                    "Owner": {"type": "rich_text", "rich_text": [{"plain_text": "infra-team"}]},
                },
            }
        ],
        "has_more": False,
        "next_cursor": None,
    }
    responses = {
        "https://api.notion.com/v1/search": search_payload,
        "https://api.notion.com/v1/blocks/page-1/children": blocks_payload,
        "https://api.notion.com/v1/databases/db-1/query": query_payload,
    }

    def fake_request(method, url, **kwargs):
        return _StubResponse(responses[url])

    monkeypatch.setattr("app.connectors.notion.client.httpx.request", fake_request)
    connector = NotionConnector()
    account = ConnectorAccount(
        id="a1",
        workspace_id="w1",
        user_id="u1",
        provider="notion",
        external_id="ext",
        display_name="Notion",
        access_token="token",
    )
    batch = connector.sync(account)
    titles = [record.title for record in batch.records]
    assert "Runbook" in titles
    assert any("Owners" in title for title in titles)
    page_record = next(r for r in batch.records if r.id == "notion-page:page-1")
    assert "# Escalation" in page_record.content
    assert "Page the on-call" in page_record.content
    assert not batch.has_more


def test_google_drive_sync_exports_documents_and_handles_failures(monkeypatch):
    files_payload = {
        "files": [
            {
                "id": "doc-1",
                "name": "Runbook",
                "mimeType": "application/vnd.google-apps.document",
                "modifiedTime": "2026-09-01T00:00:00Z",
                "webViewLink": "https://docs.google.com/doc-1",
                "owners": [{"emailAddress": "ada@example.com"}],
            },
            {
                "id": "bin-1",
                "name": "export",
                "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "modifiedTime": "2026-09-01T01:00:00Z",
                "webViewLink": "https://docs.google.com/bin-1",
            },
        ],
        "nextPageToken": "cursor-2",
    }

    def fake_request(method, url, **kwargs):
        if url.endswith("/files"):
            return _StubResponse(files_payload)
        return _StubResponse({})

    def fake_get(url, **kwargs):
        if "/export" in url:
            return _StubResponse(b"# Steps\n\nRestart first.")
        if "/files/bin-1" in url:
            return _StubResponse(b"PK\x03\x04broken")
        return _StubResponse({})

    monkeypatch.setattr("app.connectors.google_drive.client.httpx.request", fake_request)
    monkeypatch.setattr("app.connectors.google_drive.client.httpx.get", fake_get)
    connector = GoogleDriveConnector()
    account = ConnectorAccount(
        id="a1",
        workspace_id="w1",
        user_id="u1",
        provider="google_drive",
        external_id="ext",
        display_name="Drive",
        access_token="token",
    )
    batch = connector.sync(account)
    record = next(r for r in batch.records if r.id == "gdrive-file:doc-1")
    assert "Restart first" in record.content
    # The corrupt binary is skipped with a recorded failure, not a crash.
    assert batch.has_more
    assert batch.next_cursor["page_token"] == "cursor-2"


def test_teams_sync_flattens_channel_messages(monkeypatch):
    joined = {"value": [{"id": "team-1", "displayName": "Platform"}]}
    channels = {"value": [{"id": "chan-1", "displayName": "incidents"}]}
    messages = {
        "value": [
            {
                "id": "msg-1",
                "createdDateTime": "2026-09-01T10:00:00Z",
                "lastModifiedDateTime": "2026-09-01T10:00:00Z",
                "webUrl": "https://teams.example.com/msg-1",
                "from": {"user": {"displayName": "Ada"}},
                "body": {"contentType": "html", "content": "<p>Deploy is <b>live</b></p>"},
            },
            {
                "id": "msg-2",
                "createdDateTime": "2026-08-01T10:00:00Z",
                "lastModifiedDateTime": "2026-08-01T10:00:00Z",
                "body": {"content": " "},
            },
        ]
    }

    def fake_request(method, url, **kwargs):
        if url.endswith("/me/joinedTeams"):
            return _StubResponse(joined)
        if url.endswith("/channels"):
            return _StubResponse(channels)
        if url.endswith("/messages"):
            return _StubResponse(messages)
        return _StubResponse({})

    monkeypatch.setattr("app.connectors.teams.client.httpx.request", fake_request)
    connector = TeamsConnector()
    account = ConnectorAccount(
        id="a1",
        workspace_id="w1",
        user_id="u1",
        provider="teams",
        external_id="ext",
        display_name="Teams",
        access_token="token",
    )
    batch = connector.sync(account)
    record = batch.records[0]
    assert record.id == "teams-message:chan-1:msg-1"
    assert "Deploy is live" in record.content
    assert record.metadata["channel_name"] == "incidents"
    # The empty message was skipped.
    assert len(batch.records) == 1


def test_rest_pull_connector_maps_and_paginates_items(monkeypatch):
    record = {
        "id": "custom-1",
        "workspace_id": "w1",
        "created_by": "u1",
        "provider": "custom.w1.linear",
        "name": "Linear",
        "server_url": "https://api.linear.app/v1/issues",
        "version": "1.0.0",
        "oauth_json": "{}",
        "manifest_json": json.dumps(
            {
                "kind": "rest",
                "base_url": "https://api.linear.app/v1/issues",
                "items_path": "data.issues",
                "id_field": "id",
                "title_field": "title",
                "content_fields": ["description"],
                "url_field": "url",
                "updated_field": "updated_at",
                "page_param": "page",
            }
        ),
        "manifest_digest": "pending",
        "signing_key_id": "workspace-attested",
        "status": "active",
    }
    page_one = {
        "data": {
            "issues": [
                {
                    "id": "ENG-1",
                    "title": "Payments lag",
                    "description": "<p>P99 spiked after deploy</p>",
                    "url": "https://linear.app/ENG-1",
                    "updated_at": "2026-09-01",
                }
            ]
        }
    }
    page_two = {"data": {"issues": []}}

    calls = []

    def fake_get(url, headers=None, params=None, timeout=None, follow_redirects=None):
        calls.append(params)
        return _StubResponse(page_one if (params or {}).get("page", 1) == 1 else page_two)

    monkeypatch.setattr("app.connectors.rest_pull.httpx.get", fake_get)
    connector = RestPullConnector(record)
    batch = connector.sync(None)
    assert len(batch.records) == 1
    first = batch.records[0]
    assert first.title == "Payments lag"
    assert "P99 spiked after deploy" in first.content
    assert first.source_url == "https://linear.app/ENG-1"
    # Page one had items, page two was empty, so the pull stops after two calls.
    assert [call["page"] for call in calls] == [1, 2]
    assert not batch.has_more

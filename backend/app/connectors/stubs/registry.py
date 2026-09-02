from __future__ import annotations

from typing import Any


def connector_catalog() -> list[dict[str, Any]]:
    """Product-wide source and delivery catalog.

    Status is deliberately explicit: only GitHub, Slack, uploads, API, CLI,
    Python, and MCP have live paths today. Everything else stays visible
    without pretending that an OAuth button is already implemented.
    """

    return [
        {
            "provider": "github",
            "label": "GitHub",
            "category": "Code & delivery",
            "role": "source",
            "status": "live",
            "memory": ["code", "commits", "pull requests", "issues", "reviews"],
        },
        {
            "provider": "slack",
            "label": "Slack",
            "category": "Conversations",
            "role": "source_and_channel",
            "status": "live",
            "memory": ["messages", "threads", "decisions", "approved replies"],
        },
        {
            "provider": "uploads",
            "label": "Files & exports",
            "category": "Knowledge",
            "role": "source",
            "status": "live",
            "memory": ["documents", "reports", "exports", "incident notes"],
        },
        {
            "provider": "google_drive",
            "label": "Google Drive",
            "category": "Google Workspace",
            "role": "source",
            "status": "live",
            "memory": ["Docs", "Sheets", "Slides", "shared files"],
        },
        {
            "provider": "gmail",
            "label": "Gmail",
            "category": "Google Workspace",
            "role": "source_and_channel",
            "status": "next",
            "memory": ["threads", "decisions", "attachments", "approved replies"],
        },
        {
            "provider": "microsoft_365",
            "label": "Microsoft 365",
            "category": "Microsoft",
            "role": "source",
            "status": "next",
            "memory": ["SharePoint", "Word", "Excel", "OneDrive"],
        },
        {
            "provider": "teams",
            "label": "Microsoft Teams",
            "category": "Microsoft",
            "role": "source_and_channel",
            "status": "live",
            "memory": ["channel messages", "teams", "shared files"],
        },
        {
            "provider": "outlook",
            "label": "Outlook",
            "category": "Microsoft",
            "role": "source_and_channel",
            "status": "next",
            "memory": ["mail", "threads", "attachments", "approved replies"],
        },
        {
            "provider": "atlassian",
            "label": "Atlassian",
            "category": "Work management",
            "role": "source",
            "status": "next",
            "memory": ["Jira issues", "Confluence pages", "decisions", "comments"],
        },
        {
            "provider": "notion",
            "label": "Notion",
            "category": "Knowledge",
            "role": "source",
            "status": "live",
            "memory": ["pages", "databases", "database rows"],
        },
        {
            "provider": "linear",
            "label": "Linear",
            "category": "Work management",
            "role": "source",
            "status": "planned",
            "memory": ["issues", "projects", "comments"],
        },
        {
            "provider": "clickup",
            "label": "ClickUp",
            "category": "Work management",
            "role": "source",
            "status": "planned",
            "memory": ["tasks", "docs", "comments"],
        },
        {
            "provider": "buzz",
            "label": "Buzz",
            "category": "Conversations",
            "role": "source_and_channel",
            "status": "planned",
            "memory": ["messages", "threads", "approved replies"],
        },
        {
            "provider": "yahoo_mail",
            "label": "Yahoo Mail",
            "category": "Conversations",
            "role": "source_and_channel",
            "status": "planned",
            "memory": ["mail", "threads", "attachments"],
        },
        {
            "provider": "web",
            "label": "Websites & hosted documents",
            "category": "Knowledge",
            "role": "source",
            "status": "live",
            "memory": ["public web pages", "hosted PDFs", "hosted documents"],
        },
        {
            "provider": "custom_rest_source",
            "label": "Any API (custom REST source)",
            "category": "Universal ingestion",
            "role": "source",
            "status": "live",
            "memory": ["any JSON-over-HTTPS platform with scheduled pull"],
        },
        {
            "provider": "mcp",
            "label": "MCP",
            "category": "Agent surfaces",
            "role": "delivery",
            "status": "live",
            "memory": ["Cursor", "Claude", "Codex", "VS Code agents"],
        },
        {
            "provider": "api_sdk_cli",
            "label": "API, Python & CLI",
            "category": "Agent surfaces",
            "role": "delivery",
            "status": "live",
            "memory": ["context envelopes", "swarm traces", "cited answers", "work packages"],
        },
    ]


def planned_connectors() -> list[dict[str, Any]]:
    return [item for item in connector_catalog() if item["status"] != "live"]

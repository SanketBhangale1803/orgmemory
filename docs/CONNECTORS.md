# Connectors

Application login and source connectors are separate concerns: a user logs
into Runbook, then connects sources. Connector tokens are verified against
the provider before encrypted storage (Fernet).

## GitHub

- OAuth: create a GitHub OAuth App with callback
  `http://localhost:8000/api/auth/github/callback`, set `GITHUB_CLIENT_ID`
  and `GITHUB_CLIENT_SECRET`, then use **Connect with GitHub**. Scopes
  `repo read:org` allow private repository discovery.
- Token fallback: paste a fine-grained PAT in the UI or set `GITHUB_TOKEN`.
- Endpoints: `GET /api/connectors/github/auth/start`,
  `GET /api/connectors/github/auth/callback`,
  `POST /api/connectors/github/token`, `GET /api/connectors/github/status`,
  `GET /api/connectors/github/repos`, `POST /api/ingest/github`.
- Ingestion covers files, imports, endpoints, env vars, compose files,
  workflows, Jenkinsfiles, package manifests, issues, and PRs with original
  URLs; re-ingestion replaces prior repository knowledge for the project.

## Slack

- OAuth: create a Slack app with redirect
  `http://localhost:8000/api/auth/slack/callback`, set `SLACK_CLIENT_ID` and
  `SLACK_CLIENT_SECRET`. The app must be invited to private channels.
- Token fallback: bot token via UI or `SLACK_BOT_TOKEN`.
- Endpoints: `GET /api/connectors/slack/auth/start`,
  `GET /api/connectors/slack/auth/callback`,
  `POST /api/connectors/slack/token`, `GET /api/connectors/slack/status`,
  `GET /api/connectors/slack/channels`, `POST /api/ingest/slack`.
- Pasted Slack exports work without OAuth through `POST /api/ingest/upload`
  with `source_type: slack_export`.

## Uploads

`POST /api/ingest/upload` (JSON) and `POST /api/ingest/file` (multipart)
accept incidents, logs, docs, tickets, and exports. Everything flows
through the same `IngestionService` as connector data — demo data is not
special-cased.

## Ingestion jobs

All repo/Slack/upload ingestion is job-recorded (`queued/running/succeeded/
failed/partial`) with files/issues/PRs scanned, graph nodes/edges written,
warnings, and errors: `GET /api/ingest/jobs`, `GET /api/ingest/jobs/{id}`.

## Planned connectors

Gmail, ClickUp, Jira, Linear, Notion, Google Drive, and Zendesk have
registry entries that render honestly in the UI as planned/not configured.
No connector ever pretends to be connected.

## Incident-tool importers

The migration layer (`app/importers`) is a connector class of its own:
PagerDuty has a live REST importer (incidents, services) activated by
`PAGERDUTY_API_TOKEN`; Rootly, incident.io, Opsgenie, Statuspage, Jira
Service Management, and ServiceNow expose the same
`IncidentToolImporter` interface and report `not_connected` /
not-implemented rather than faking imports. See `/api/importers`.

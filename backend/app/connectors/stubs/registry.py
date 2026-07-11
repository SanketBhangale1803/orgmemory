def planned_connectors() -> list[dict[str, str]]:
    return [
        {"provider": name, "status": "planned"}
        for name in ["gmail", "clickup", "jira", "linear", "notion", "google_drive", "zendesk"]
    ]
